"""The agent object.

The agent orchestrates the user-assistant turns and delegates the actual turn
handling to the core.
"""

import json
import os
import sys
import time
import tiktoken
import openai

from rich import box, inspect
from rich.prompt import Prompt
from rich.panel import Panel
from rich.align import Align
from rich.markdown import Markdown
from rich.panel import Panel

from pathlib import Path
from xdg_base_dirs import xdg_data_home

from agent.core import Core, Stage, TurnCancelled
from agent.console import console


# Try to import prompt_toolkit for rich input; fall back to plain input.
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style
    from prompt_toolkit.completion import FuzzyWordCompleter
    from prompt_toolkit.clipboard import InMemoryClipboard
    from prompt_toolkit.formatted_text import HTML
    _HAS_PROMPT_TOOLKIT = True

except ImportError:
    console.print("[red]ERROR:[/red] could not initialize promtp toolkit")
    _HAS_PROMPT_TOOLKIT = False


txt_goodbye = "\n[bold blue]Goodbye![/bold blue]"

def prompt_callback(stage:Stage):
    """Called when starting and ending prompt processing for a given turn"""
    match stage:
        case Stage.START.value:
            self.spinner_prompt = console.status("⏳ Processing prompt...")
            self.spinner_prompt.start()
        case Stage.STOP.value:
            self.spinner_prompt.stop()
            self.spinner_prompt = None
            console.print("[green]✓[/] ⏳ Prompt processed")
        case _:
            raise RuntimeError(f"Prompt callback only has Start and Stop stages: {stage}")

def reasoning_callback(stage:Stage, content:str=None, show_thinking:bool=True):
    """Called when starting, processing, and ending the reasoning stage."""
    match stage:
        case Stage.START.value:
            if show_thinking:
                console.print("[orange1]⇨[/] 💡 Thinking...")
            else:
                self.spinner_thinking = console.status("💡 Thinking...")
                self.spinner_thinking.start()
                
        case Stage.PROCESS.value:
            if show_thinking:
                console.print(f"[grey39]{delta.reasoning_content}[/]", end="")

        case Stage.STOP.value:
            if self.spinner_thinking:
                self.spinner_thinking.stop()
                self.spinner_thinking = None
            console.print("[green]✓[/] 💡 Done thinking")

def content_callback(content:str=None):
    """Called when new chunks arrive in streaming mode."""
    console.print(content, end="")

def tool_callback(tool_name:str, tool_args):
    console.print(f"[black on #66aa99] ⚙ Activating tool: {tool_name} [/black on #66aa99]")
    a = 1

def cancel_callback():
    a = 1

def error_callback():
    a = 1

class Agent:
    def __init__(self, config_path=None):
        self.core = Core(config_path)


    def _statusline(self, total_tokens, ntools, total_gen_time):
        console.print(f"[black on #777777]   {total_gen_time:.1f}s  ⬤  {total_tokens} tokens  ⬤  {ntools} tools   [/black on #777777]", justify="full")
        console.print()

        
    def _create_prompt_session(self):
        # Key bindings: 
        kb = KeyBindings()
        @kb.add('enter')
        def _(event):
            """Enter submits the input."""
            event.current_buffer.validate_and_handle()
        @kb.add('escape', 'enter')
        def _(event):
            """Alt+Enter inserts a newline."""
            event.current_buffer.insert_text('\n')

        # Create prompt session now
        style = Style.from_dict({
            "prompt": "ansiyellow",
            "frame.border": "ansiyellow",
        })

        # Vi mode
        vi_mode = self.config.get("agent.vi_mode", False)

        # Slash commands autocompleter
        commands = [cmd.name for cmd in registry.list_commands()]
        slash_completer = FuzzyWordCompleter(commands)

        # History path
        history_path = xdg_data_home() / "langur-agent" / "history.txt"
        history_path.parent.mkdir(parents=True, exist_ok=True)

        # Toolbar
        prompt_toolbar = lambda : HTML(" <b>Alt</b>+<b>Enter</b>: new line | <b>Enter</b>: submit prompt | <b>Ctrl</b>+<b>C</b>: quit")

        return PromptSession(
                    style=style,
                    message="⩥ You ⩤\n❯ ",
                    history=FileHistory(str(history_path)),
                    show_frame=True,
                    multiline=True,
                    key_bindings=kb,
                    vi_mode=vi_mode,
                    clipboard=InMemoryClipboard(),
                    enable_open_in_editor=vi_mode,
                    complete_while_typing=True,        
                    complete_in_thread=True,
                    completer=slash_completer,
                    auto_suggest=AutoSuggestFromHistory(),
                    bottom_toolbar=prompt_toolbar,
        )
        
    def run_interactive(self):
        """Run the agent in interactive mode."""
        import shutil
        term_size = shutil.get_terminal_size((80, 20))
        if term_size.columns < 80:
            languragent="LANGUR AGENT"
        else:
            languragent = '''
██      ▄▄▄  ▄▄  ▄▄  ▄▄▄▄ ▄▄ ▄▄ ▄▄▄▄    ▄████▄  ▄▄▄▄ ▄▄▄▄▄ ▄▄  ▄▄ ▄▄▄▄▄▄
██     ██▀██ ███▄██ ██ ▄▄ ██ ██ ██▄█▄   ██▄▄██ ██ ▄▄ ██▄▄  ███▄██   ██  
██████ ██▀██ ██ ▀██ ▀███▀ ▀███▀ ██ ██   ██  ██ ▀███▀ ██▄▄▄ ██ ▀██   ██  
            '''
        title = Align.center(f"[bold blue]{languragent}[/bold blue]", vertical='middle')
        console.print(Panel(title, box=box.HEAVY, border_style="blue"))
        console.print()
        console.print(registry.get_commands_str())

        if _HAS_PROMPT_TOOLKIT:
            sefl.session = self._create_prompt_session()
        
        if self._session:
            # Prompt Toolkit
            style = Style.from_dict({
                "prompt": "ansiyellow",
            })
            get_input = lambda: str(
                self._session.prompt()
            ).strip()
        else:
            # Rich
            get_input = lambda: Prompt.ask(prompt="[yellow]⩥ You ⩤[/yellow]\n❯",
                                           console=console)

        # Main loop
        while True:
            try:
                user_input = get_input()
            except (EOFError, KeyboardInterrupt):
                console.print(txt_goodbye)
                break

            if not user_input:
                continue

            # Process slash commands
            if user_input.startswith("/"):
                tokens = user_input.split()
                command, params = registry.lookup(tokens)

                if command:
                    ok, msg, content, should_exit = registry.execute(self, command, params)
                    if should_exit:
                        console.print(txt_goodbye)
                        break
                    if ok:
                        if msg:
                            console.print(f"[green]OK[/green]: {msg}")
                        if content:
                            console.print(content)
                        console.print()
                    else:
                        if msg:
                            console.print(f"[red]ERROR[/red]: {msg}")
                else:
                    console.print(f"[red]ERROR:[/red] command not found: {user_input}")
                    
                continue

            else:
                console.print(f"\n[magenta]⩥ Agent ⩤ [/magenta]  ⦗[blue]{self.config.get('model.name')}[/blue]⦘")
                console.print("  [dim][bold]Ctrl[/bold]+[bold]C[/bold]: Cancel turn[/dim]\n")
                (response, total_tokens, ntools, total_gen_time) = self.core.run_turn(user_input,
                                                                                      prompt_callback,
                                                                                      reasoning_callback,
                                                                                      content_callback,
                                                                                      tool_callback,
                                                                                      cancel_callback,
                                                                                      error_callback
                                                                                  )
                console.print()
                if response == "[Cancelled]":
                    continue  # skip status line, go straight back to prompt
                self._statusline(total_tokens, ntools, total_gen_time)

        # Persist memory on session exit
        self.memory.save()

    def get_models(self):
        """Gets a list with all the available models."""
        return self.client.models.list()

    def set_model(self, model_name):
        """Sets the model to use."""
        models = self.get_models()
        for model in models:
            if model_name == model.id:
                # Match, set and return
                self.config.set("model.name", model_name)
                return

        raise NameError(f"the model '{model_name}' does not exsit")
        
