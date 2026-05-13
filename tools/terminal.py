"""Terminal execution tool.

Allows the agent to run shell commands on the host machine.
Usage: run_command(command="ls -la", timeout=30)

Security: commands run in the current working directory.
"""

import subprocess
import json
from agent.tools import register_tool


def run_command_handler(args):
    """Execute a shell command and return its output."""
    command = args.get("command", "")
    timeout = args.get("timeout", 30)

    if not command:
        return {"error": "No command provided"}

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
        if result.returncode == 0:
            output["success"] = True
        else:
            output["success"] = False
        return output
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


register_tool(
    name="run_command",
    description=(
        "Execute a shell command and return the output. "
        "Use this when you need to run terminal commands, execute scripts, "
        "or interact with the filesystem via shell."
    ),
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds (default: 30)",
            },
        },
        "required": ["command"],
    },
    handler=run_command_handler,
)
