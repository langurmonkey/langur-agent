from rich.console import Console
from rich.theme import Theme
from rich.traceback import install

# Replace default error tracebacks with better version
install()

# Theme
langur_theme = Theme({
    "title": "bold deep_sky_blue3",

    # Global
    "accent": "deep_sky_blue3",
    "accent-bold": "bold deep_sky_blue3",
    "output-frame": "medium_orchid",

    # Turns
    "agent": "medium_orchid",
    "user": "gold1",

    "tool": "steel_blue3",
    "status": "white on grey15",
    "weak": "grey39",
    "kbd": "light_pink1 bold on grey15", 

    "list-item": "cyan",
    "list-desc": "grey39",

    # Logging
    "ok": "chartreuse4",
    "info": "dim cyan",
    "warn": "orange_red1",
    "warning": "orange_red1",
    "error": "bold red",
    "err": "bold red"
})

# Create console
console = Console(theme=langur_theme)

