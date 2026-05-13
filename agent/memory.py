"""Simple file-based memory system.

Stores user profile and persistent notes as JSON.
Follows XDG Base Directory spec:
- Data: $XDG_DATA_HOME/langur-agent/memory/

Design: memory is buffered in memory. Changes are persisted to disk
when save() is called. On init, state is loaded from disk.
"""

import json
from pathlib import Path
from xdg_base_dirs import xdg_data_home

DEFAULT_MEMORY_DIR = xdg_data_home() / "langur-agent" / "memory"

# Singleton instance
_instance = None


class Memory:
    """Persistent memory with in-memory buffering.

    Singleton: all Memory() calls return the same instance, so in-memory
    state is shared between the agent and tool handlers.
    """

    def __new__(cls, memory_dir=None):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
        return _instance

    def __init__(self, memory_dir=None):
        # Only initialize on first creation
        if hasattr(self, "_initialized"):
            return
        self.memory_dir = Path(memory_dir) if memory_dir else DEFAULT_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._user_profile_path = self.memory_dir / "user_profile.json"
        self._notes_path = self.memory_dir / "notes.json"

        # Load from disk into memory buffers
        self._user_profile = self._load_json(self._user_profile_path, {})
        self._notes = self._load_json(self._notes_path, [])
        self._initialized = True

    def _load_json(self, path, default):
        """Load JSON from file, returning default if not found or invalid."""
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return default
        return default

    def save(self):
        """Persist in-memory state to disk.

        This is the authoritative write — all changes are buffered
        in memory and only written here.
        """
        with open(self._user_profile_path, "w") as f:
            json.dump(self._user_profile, f, indent=2)

        with open(self._notes_path, "w") as f:
            json.dump(self._notes, f, indent=2)

    def get_user_profile(self):
        """Return the in-memory user profile."""
        return self._user_profile

    def set_user_profile(self, data):
        """Update the in-memory user profile. Call save() to persist."""
        if isinstance(data, dict):
            self._user_profile = data
        else:
            self._user_profile = {**self._user_profile, **data}

    def get_notes(self):
        """Return the in-memory notes list."""
        return self._notes

    def add_note(self, content, category="general"):
        """Add a note to in-memory buffer. Call save() to persist."""
        note = {
            "category": category,
            "content": content,
            "id": len(self._notes) + 1,
        }
        self._notes.append(note)
        return note

    def get_formatted(self):
        """Return all memory formatted for the system prompt."""
        lines = []

        if self._user_profile:
            lines.append("## User Profile")
            for key, value in self._user_profile.items():
                lines.append(f"- {key}: {value}")

        if self._notes:
            lines.append("\n## Persistent Notes")
            for note in self._notes:
                lines.append(f"- [{note['category']}] {note['content']}")

        return "\n".join(lines) if lines else None
