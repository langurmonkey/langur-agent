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

    def __new__(cls, max_chat_history=128000, memory_dir=None):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
        return _instance

    def __init__(self, max_chat_history=128000, memory_dir=None):
        # Only initialize on first creation
        if hasattr(self, "_initialized"):
            return
        self.memory_dir = Path(memory_dir) if memory_dir else DEFAULT_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._user_profile_path = self.memory_dir / "user_profile.json"
        self._notes_path = self.memory_dir / "notes.json"
        self._chat_history = ChatMemory(max_chars=max_chat_history, memory_dir=self.memory_dir)

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

        self._chat_history.save()

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

    def get_formatted_chat(self):
        return self._chat_history.get_formatted()

    def add_chat_exchange(self, role, content):
        self._chat_history.add_exchange(role, content)


class ChatMemory:
    """Rolling chat memory that stores recent exchanges.
    
    Maintains a rolling window of recent user input/assistant output pairs,
    limited by character count from configuration. Automatically trimmed
    when the window is exceeded. Persisted to disk.
    """
    
    def __init__(self, max_chars=128000, memory_dir=None):
        """Initialize chat memory.
        
        Args:
            max_chars: Maximum total characters to keep in memory (default: 128000)
            memory_dir: Directory to persist chat history (default: ~/.local/share/langur-agent/memory/)
        """
        self._exchanges = []  # list of {"role": "user"|"assistant", "content": str}
        self.max_chars = max_chars
        self.total_chars = 0
        
        # Set up persistence
        if memory_dir is None:
            self.memory_dir = DEFAULT_MEMORY_DIR
        else:
            self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._chat_path = self.memory_dir / "chat_history.json"
        
        # Load from disk
        self._load()
    
    def _load(self):
        """Load chat history from disk."""
        if self._chat_path.exists():
            try:
                with open(self._chat_path, "r") as f:
                    data = json.load(f)
                    self._exchanges = data.get("exchanges", [])
                    self.total_chars = sum(len(e["content"]) for e in self._exchanges)
            except (json.JSONDecodeError, IOError):
                pass
    
    def save(self):
        """Persist in-memory state to disk."""
        with open(self._chat_path, "w") as f:
            json.dump({"exchanges": self._exchanges}, f, indent=2)
    
    def add_exchange(self, role, content):
        """Add a user input or assistant output to memory.
        
        Args:
            role: "user" or "assistant"
            content: The text content
        """
        char_count = len(content)
        
        # Add the new exchange
        self._exchanges.append({
            "role": role,
            "content": content,
        })
        self.total_chars += char_count
        
        # Trim if exceeded
        if self.total_chars > self.max_chars:
            self._trim()
        
        # Persist immediately
        self.save()
    
    def _trim(self):
        """Remove oldest exchanges until under the character limit."""
        print("Trimming memory...")
        while self.total_chars > self.max_chars and self._exchanges:
            oldest = self._exchanges.pop(0)
            self.total_chars -= len(oldest["content"])
        
        # Save after trimming
        self.save()
    
    def get_formatted(self):
        """Return chat history formatted for the system prompt.
        
        Returns:
            Formatted string of recent exchanges, or None if empty
        """
        if not self._exchanges:
            return None
        
        lines = ["## Recent Conversation"]
        # Show most recent exchanges first (last 10)
        recent = self._exchanges[-10:]
        for exchange in recent:
            role_label = "User" if exchange["role"] == "user" else "Assistant"
            # Truncate very long messages
            content = exchange["content"]
            if len(content) > 500:
                content = content[:500] + "... (truncated)"
            lines.append(f"### {role_label}")
            lines.append(content)
            lines.append("---")
        
        return "\n".join(lines)
