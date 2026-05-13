#!/usr/bin/env python3
"""Langur Agent - entry point."""

import sys
from pathlib import Path

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from agent.agent import Agent


def main():
    """Run the agent interactively or as a one-shot query."""
    config_path = None

    if "-c" in sys.argv or "--config" in sys.argv:
        idx = sys.argv.index("-c") if "-c" in sys.argv else sys.argv.index("--config")
        config_path = sys.argv[idx + 1]

    try:
        agent = Agent(config_path=config_path)
    except:
        return

    # One-shot mode: python main.py "your query"
    if len(sys.argv) > 1 and sys.argv[1] not in ("-c", "--config"):
        query = " ".join(sys.argv[1:])
        response = agent.run(query)
        print(response)
        return

    # Interactive mode
    agent.run_interactive()


if __name__ == "__main__":
    main()
