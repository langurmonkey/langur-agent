#!/usr/bin/env python3
"""Langur Agent - entry point."""

import sys
import time
from pathlib import Path

# Ensure the project root (parent of agent/) is on the path
# This handles both pip-installed and direct execution
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent import Agent


def main():
    """Run the agent interactively or as a one-shot query."""
    config_path = None

    if "-c" in sys.argv or "--config" in sys.argv:
        idx = sys.argv.index("-c") if "-c" in sys.argv else sys.argv.index("--config")
        config_path = sys.argv[idx + 1]

    try:
        agent = Agent(config_path=config_path)
    except Exception as e:
        print("Error creating agent", e)
        return

    # One-shot mode: langur-agent "your query"
    if len(sys.argv) > 1 and sys.argv[1] not in ("-c", "--config"):
        query = " ".join(sys.argv[1:])
        result = agent.run(query)
        # run() returns (text, total_tokens, ntools, total_gen_time) tuple
        if isinstance(result, tuple):
            print(result[0])
            if len(result) > 3:
                print(f"\n[black on #777777]  ⬤  {result[3]:.1f}s  ⬤  {result[1]} tokens  ⬤  {result[2]} tools  [/black on #777777]")
        else:
            print(result)
        return

    # Interactive mode
    agent.run_interactive()


if __name__ == "__main__":
    main()
