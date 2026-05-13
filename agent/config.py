"""Load configuration from config.yaml.

Follows XDG Base Directory spec:
- Config: ~/.config/langur-agent/config.yaml
- Fallback: if not found, copies ./config.yaml there
- If neither exists, returns defaults
"""

import os
import shutil
import yaml
from rich import print
from pathlib import Path
from xdg_base_dirs import xdg_config_home

DEFAULT_CONFIG = Path(__file__).parent.parent / "config.yaml"
XDG_CONFIG_DIR = xdg_config_home() / "langur-agent"
XDG_CONFIG_FILE = XDG_CONFIG_DIR / "config.yaml"


def _ensure_xdg_config():
    """Ensure XDG config directory exists, copy ./config.yaml if needed."""
    if XDG_CONFIG_FILE.exists():
        return XDG_CONFIG_FILE

    XDG_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if DEFAULT_CONFIG.exists():
        shutil.copy2(DEFAULT_CONFIG, XDG_CONFIG_FILE)
        return XDG_CONFIG_FILE

    return XDG_CONFIG_FILE  # will be created on first write

def get_default_config_path():
    return _ensure_xdg_config()

def load_config(path=None):
    """Load config from YAML file."""
    if path:
        config_path = Path(path)
    else:
        config_path = _ensure_xdg_config()

    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    # Defaults if no config file
    return {
        "model": {
            "provider": "openai",
            "name": "gpt-4o-mini",
            "api_key": os.environ.get("LANGUR_API_KEY", ""),
            "base_url": "",
            "context_length": 128000,
        },
        "agent": {
            "max_turns": 50,
            "personality": "You are a helpful assistant.",
        },
    }

def log_config():
    path = get_default_config_path()
    content = load_config()
    print(f"[bold]Config file[/bold]: [blue]{path}[/blue]")
    print()
    print(content)

