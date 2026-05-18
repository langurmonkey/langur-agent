"""Centralized slash command registry for langur-agent."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class Command:
    """A single slash command definition."""
    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    handler: Callable = None  # (agent, params: list[str]) -> str | None
    can_complete: bool = False


class CommandRegistry:
    """Module-level singleton registry for slash commands."""

    def __init__(self):
        self._commands: dict[str, Command] = {}  # primary name -> Command

    def register(self, cmd: Command) -> None:
        """Register a command and all its aliases."""
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd  # alias points to same Command

    def lookup(self, name: str) -> Optional[Command]:
        """Look up a command by name or alias (case-insensitive)."""
        return self._commands.get(name.lower())

    def execute(self, agent, name: str, params: list[str]):
        """Execute a command. Returns (result_string | None, should_exit)."""
        cmd = self.lookup(name)
        if cmd is None:
            return None, False
        result = cmd.handler(agent, params)
        should_exit = name.lower() in ("/quit", "/exit", "/q")
        return result, should_exit

    def list_commands(self) -> list[Command]:
        """Return all unique commands (deduplicated by primary name)."""
        seen = set()
        result = []
        for cmd in self._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(cmd)
        return result

    def names(self) -> list[str]:
        """Return all command names (primary + aliases) for completion."""
        return list(self._commands.keys())


# Module-level singleton
registry = CommandRegistry()


# --- Built-in command handlers ---

def _cmd_quit(agent, params):
    return "EXIT"


def _cmd_note(agent, params):
    if params:
        agent.memory.add_note(" ".join(params))
        return "[green]OK:[/] note added successfully"
    return "[red]ERROR:[/] please, provide a note: '/note This is my note'"


def _cmd_notes(agent, params):
    notes = agent.memory.get_notes()
    return "\n".join(f"⬤ {note['id']} ({note['category']}): {note['content']}" for note in notes)


def _cmd_memory(agent, params):
    return agent.memory.get_formatted() + agent.memory.get_formatted_chat()


def _cmd_tools(agent, params):
    from agent.tools import log_tools
    log_tools()
    return None


def _cmd_skills(agent, params):
    agent.skills.log_skills()
    return None


def _cmd_config(agent, params):
    from agent.config import log_config
    log_config()
    return None


def _cmd_vi(agent, params):
    if params:
        vi = params[0].lower() == "on"
        agent.config.get("agent")["vi_mode"] = vi
        agent._create_prompt_session()
        return f"[green]OK:[/] vi mode: {vi}"
    return "[red]ERROR:[/] /vi command needs a parameter (on/off): '/vi on', '/vi off'"


def _cmd_help(agent, params):
    agent.print_help()
    return None


# --- Register all commands ---
registry.register(Command("/quit", ["/exit", "/q"], "Exit the agent", _cmd_quit))
registry.register(Command("/note", [], "Save a note to memory", _cmd_note))
registry.register(Command("/notes", [], "List all notes", _cmd_notes))
registry.register(Command("/memory", [], "List memory contents", _cmd_memory))
registry.register(Command("/tools", [], "List available tools", _cmd_tools))
registry.register(Command("/skills", [], "List loaded skills", _cmd_skills))
registry.register(Command("/config", [], "Print configuration", _cmd_config))
registry.register(Command("/vi", [], "Toggle vi mode (on/off)", _cmd_vi))
registry.register(Command("/help", ["/commands"], "Show command help", _cmd_help, can_complete=True))
