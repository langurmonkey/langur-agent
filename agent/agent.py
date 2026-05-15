"""Core agent loop.

The agent:
1. Builds a system prompt (personality + skills + tools + memory)
2. Sends messages to the LLM
3. Handles tool calls or returns the final text response
4. Loops until max turns or a text response
"""

import json
import os
import sys
import time
# Counting tokens
import tiktoken

from rich import print, box, inspect
from rich.prompt import Prompt
from rich.panel import Panel
from rich.align import Align
from pathlib import Path
from xdg_base_dirs import xdg_data_home

import openai

from agent.config import load_config, log_config
from agent.memory import Memory
from agent.skills import SkillLoader
from agent.tools import get_tool_schemas, execute_tool, log_tools

# Try to import prompt_toolkit for rich input; fall back to plain input.
try:
    from prompt_toolkit import prompt
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.styles import Style
    _HAS_PROMPT_TOOLKIT = True
except ImportError:
    _HAS_PROMPT_TOOLKIT = False

class Agent:
    """Simple LLM agent with tools, skills, and memory."""

    def __init__(self, config_path=None):
        self.config = load_config(config_path)
        model_cfg = self.config.get("model", {})
        agent_cfg = self.config.get("agent", {})

        # Initialize OpenAI client
        api_key = model_cfg.get("api_key") or os.environ.get("LANGUR_API_KEY", "")
        base_url = model_cfg.get("base_url")
        # Auto-append /v1 for LM Studio / local API servers
        if base_url and not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        try:
            self.client = openai.OpenAI(api_key=api_key, base_url=base_url or None)
        except openai.OpenAIError as err:
            print(f"[red]ERROR[/red]: OpenAI endpoint creation: {err}")
            raise Exception(f"{err}")

        # Agent settings
        self.model = model_cfg.get("name", "qwen/qwen3.6-35b-a3b")
        self.max_turns = agent_cfg.get("max_turns", 50)
        self.personality = agent_cfg.get("system_prompt", "You are a helpful assistant, expert in many areas of science. Respond concisely and to the point. No fluff.")
        self.stream = agent_cfg.get("stream", True)
        max_chat_history = agent_cfg.get("max_chat_history", 128000)

        # Initialize subsystems
        self.memory = Memory(max_chat_history=max_chat_history)
        self.skills = SkillLoader()

        # Conversation history
        self.messages = []

        # Initialize tokenizer for token-counting
        encoding_name = "cl100k_base"
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            print(f"[red]ERROR[/red]: Error loading tokenizer: {e}")
            raise Exception(f"{e}")

    def _build_system_prompt(self):
        """Build the system prompt with personality, skills, and memory."""
        parts = [self.personality]

        # Add formatted memory
        memory_text = self.memory.get_formatted()
        if memory_text:
            parts.append(memory_text)

        # Add chat history
        chat_text = self.memory.get_formatted_chat()
        if chat_text:
            parts.append(chat_text)

        # Add skills
        skills_text = self.skills.load_all()
        if skills_text:
            parts.append(skills_text)

        return "\n".join(parts)

    def _send_to_llm(self, stream=False):
        """Send messages to the LLM and get a response.

        Args:
            stream: If True, print tokens as they arrive and return a
                    dict with 'text' and 'tool_calls' keys. If False,
                    return the raw message object.
        """
        tools = get_tool_schemas()
        start = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=tools if tools else None,
                tool_choice="auto",
                stream=stream,
            )
        except Exception as e:
            raise RuntimeError(
                f"LLM API error (model={self.model}, base_url={self.client.base_url}): {e}"
            ) from e

        if stream:
            # Collect streamed tokens and tool calls
            full_text = ""
            tool_calls = {}  # indexed by position to merge partial deltas
            first_chunk_time = None

            for chunk in response:
                delta = chunk.choices[0].delta
                now = time.time()

                # Track when first chunk arrives (excludes request send time)
                if first_chunk_time is None:
                    first_chunk_time = now

                # Collect text
                if delta.content:
                    full_text += delta.content

                    # Print text
                    print(delta.content, end="", flush=True)

                # Collect tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls:
                            tool_calls[idx] = {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.function.name:
                            tool_calls[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls[idx]["function"]["arguments"] += tc.function.arguments

            # Newline
            print()

            # Count tokens using tiktoken (LM Studio streaming doesn't include usage)
            tokens = 0
            if self.encoding and full_text:
                tokens = len(self.encoding.encode(full_text))

            # Elapsed time: from first chunk to last chunk (generation time only)
            if first_chunk_time is not None:
                gen_elapsed = now - first_chunk_time
            else:
                gen_elapsed = time.time() - start
            if gen_elapsed <= 0:
                gen_elapsed = 1  # avoid division by zero
            
            # No debug output

            # Convert indexed dict to list
            tc_list = list(tool_calls.values()) if tool_calls else None

            return ({"text": full_text, "tool_calls": tc_list}, tokens, gen_elapsed)
        # Non-streaming: return message object
        if not response.choices:
            raise RuntimeError(
                f"LLM returned no choices. Model: {self.model}, "
                f"base_url: {self.client.base_url}. "
                f"Check that the model name matches a loaded model in LM Studio. "
                f"Response: {response}"
            )

        tokens = response.choices[0].message.usage.completion_tokens
        gen_elapsed = time.time() - start
        return (response.choices[0].message, tokens, gen_elapsed)

    def run(self, user_input):
        """Run a turn interaction with a user message.

        Args:
            user_input: The user's message string.

        Returns:
            The final text response from the LLM.
        """
        # Record start time
        start = time.time()

        # Record user input in chat memory
        self.memory.add_chat_exchange("user", user_input)

        # Initialize with system prompt
        self.messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_input},
        ]

        # Total token count
        total_tokens = 0
        # Total generation time (excludes network latency, prompt building, etc.)
        total_gen_time = 0
        # Tool usages
        ntools = 0
        for turn in range(self.max_turns):
            # Send to LLM
            (result, tokens, gen_elapsed) = self._send_to_llm(stream=self.stream)
            total_tokens += tokens
            total_gen_time += gen_elapsed

            # Normalize tool calls from both streaming (plain dicts) and
            # non-streaming (OpenAI API objects) into a common format
            if isinstance(result, dict):
                # Streaming mode: result is {"text": ..., "tool_calls": ...}
                response_text = result.get("text", "")
                raw_tool_calls = result.get("tool_calls")
            else:
                # Non-streaming mode: result is a message object
                response_text = result.content or ""
                raw_tool_calls = result.tool_calls

            # Normalize tool calls to plain dicts
            tool_calls = []
            if raw_tool_calls:
                for tc in raw_tool_calls:
                    if isinstance(tc, dict):
                        # Already a plain dict from streaming
                        tool_calls.append(tc)
                    else:
                        # OpenAI API object — convert to dict
                        tool_calls.append({
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        })

            # Handle tool calls
            if tool_calls:
                # Append the assistant message with tool calls as plain dicts
                self.messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": tool_calls,
                })

                # Execute each tool call
                for tc in tool_calls:
                    ntools = ntools + 1
                    tool_name = tc["function"]["name"]
                    tool_args = tc["function"]["arguments"]

                    print(f"[black on #66aa99] ⚙ Activating tool: {tool_name} [/black on #66aa99]")
                    result = execute_tool(tool_name, json.loads(tool_args) if isinstance(tool_args, str) else tool_args)

                    # Append tool result
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                continue  # Loop back to LLM with tool results

            # No tool calls - this is the final response
            self.messages.append({"role": "assistant", "content": response_text})
            
            # Record assistant output in chat memory
            self.memory.add_chat_exchange("assistant", response_text)
            # Persist memory
            self.memory.save()
            
            return (response_text, total_tokens, ntools, total_gen_time)

        # Max turns reached!
        # Persist memory
        self.memory.save()
        return "I've reached the maximum number of turns. Please rephrase your request."

    def _statusline(self, total_tokens, ntools, total_gen_time):
        print(f"[black on #777777]  ⬤  {total_gen_time:.1f}s  ⬤  {total_tokens} tokens  ⬤  {ntools} tools  [/black on #777777]")
        print()

    def print_help(self):
        print(f"⬤ [green]/q[/], [green]/quit[/], [green]/exit[/]   → exit")
        print(f"⬤ [green]/tools[/]             → list tools")
        print(f"⬤ [green]/skills[/]            → list skills")
        print(f"⬤ [green]/config[/]            → print configuration")
        print(f"⬤ [green]/help[/], [green]/commands[/]   → print command help")
        print()
        

    def run_interactive(self):
        """Run the agent in interactive mode."""
        title = Align.center("[bold blue]LANGUR AGENT[/bold blue]", vertical='middle')
        print(Panel(title, box=box.HEAVY, subtitle="The dead-simple AI agent for local workflows", border_style="yellow"))
        print()
        self.print_help()

        # Set up prompt_toolkit if available
        history_path = xdg_data_home() / "langur-agent" / "history.txt"
        history_path.parent.mkdir(parents=True, exist_ok=True)

        if _HAS_PROMPT_TOOLKIT:
            style = Style.from_dict({
                "prompt": "ansiyellow",
            })
            get_input = lambda: str(
                prompt(style=style,
                       message=":: You ::\n❯ ",
                       history=FileHistory(str(history_path)),
                       complete_while_typing=True)
            ).strip()
        else:
            get_input = lambda: Prompt.ask("[yellow]:: You ::[/]\n❯ ")

        while True:
            try:
                user_input = get_input()
            except (EOFError, KeyboardInterrupt):
                print(f"\n[bold blue]Goodbye![/]")
                break

            if not user_input:
                continue

            # SPECIAL COMMANDS
            if user_input.startswith("/") and len(user_input.split()) == 1:
                if user_input.lower() in ["/quit", "/exit", "/q"]:
                    print(f"\n[bold blue]Goodbye![/]")
                    break
                elif user_input.lower() in ["/tools"]:
                    log_tools()
                elif user_input.lower() in ["/skills"]:
                    self.skills.log_skills()
                elif user_input.lower() in ["/config"]:
                    log_config()
                elif user_input.lower() in ["/help", "/commands"]:
                    self.print_help()
                else:
                    print(f"[red]ERROR:[/red] unknown command: {user_input}")
                    print()
                    print("Avaliable commands:")
                    self.print_help()
            else:

                print(f"\n[magenta]:: Agent :: [/magenta]\n", end="", flush=True)
                (response, total_tokens, ntools, total_gen_time) = self.run(user_input)
                print()
                self._statusline(total_tokens, ntools, total_gen_time)

        # Persist memory on session exit
        self.memory.save()
