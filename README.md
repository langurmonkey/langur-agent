# Langur AI agent

A dead-simple, extensible AI agent for Linux with tools, skills, and persistent memory. Created as a learning tool.

## Architecture

```
langur-agent/
├── main.py              # Entry point (interactive or one-shot)
├── config.yaml          # Model & agent configuration
├── requirements.txt     # Dependencies
├── langur/              # Core agent code
│   ├── agent.py         # Main agent loop
│   ├── config.py        # Config loader
│   ├── memory.py        # Persistent memory (JSON)
│   ├── skills.py        # Skills loader (markdown)
│   └── tools.py         # Tool registry & discovery
└── tools/               # Tool implementations
    └── basic.py         # Example tools
└── skills/              # Skill definitions
    └── example.md       # Example skill
```

## Quick Start

```bash
# Install dependencies
uv sync

# Set your API key
export LANGUR_API_KEY="your-key-here"

# Interactive mode
uv run python main.py

# One-shot query
uv run python main.py "What is the capital of France?"
```

## Adding Tools

Create a file in `tools/` and call `register_tool()`:

```python
from langur.tools import register_tool

def my_handler(args):
    return {"result": "hello"}

register_tool(
    name="my_tool",
    description="Does something useful",
    parameters={
        "type": "object",
        "properties": {"input": {"type": "string"}},
        "required": ["input"],
    },
    handler=my_handler,
)
```

Tools are auto-discovered on startup.

## Adding Skills

Add a `.md` file in `skills/` with YAML front matter, following the [agentskills.io](https://agentskills.io) standard:

```markdown
---
name: my-skill
description: What this skill does
---

# My Skill

## When to Use

...

## Steps

1. ...
```

The front matter `name` and `description` are parsed and shown in the
skills list. The body is injected into the system prompt.

## Memory

Persistent memory follows XDG Base Directory spec in `~/.local/share/langur-agent/memory/`:
- `user_profile.json` — user information
- `notes.json` — persistent notes (added via `save_note` tool)

**Lifecycle:**
- Memory is loaded into the system prompt each turn
- `save_note` tool adds notes during a session
- `save_memory` tool explicitly persists memory to disk
- Memory is auto-saved when the agent exits (interactive mode)

Memory is loaded into the system prompt each turn.

## Config

Config follows XDG Base Directory spec in `~/.config/langur-agent/config.yaml`.
On first run, `./config.yaml` is copied there if it exists.

Edit with:
```bash
nano ~/.config/langur-agent/config.yaml
```
