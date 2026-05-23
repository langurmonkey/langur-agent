# rich_ui.py — add this as a new file or inline in agent.py
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.console import Group
from datetime import datetime


class RichUI:
    """Manages the three-panel Rich layout (header / content / toolbar)."""

    def __init__(self, refresh_per_second=8):
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="content", ratio=1),
            Layout(name="toolbar", size=3),
        )
        self.live = Live(self.layout, refresh_per_second=refresh_per_second, screen=True)
        self.content_buffer = ""
        self.reasoning_buffer = ""

        # Initialize panels
        self._update_header("AI Assistant")
        self._update_content("Ready", title="Session")
        self._update_toolbar("Idle", mode="IDLE")

    def __enter__(self):
        self.live.__enter__()
        return self

    def __exit__(self, *args):
        self.live.__exit__(*args)

    # --- Header ---
    def _update_header(self, title: str):
        self.layout["header"].update(
            Panel(f"[bold white]{title}[/]", style="white on blue")
        )

    # --- Content ---
    def _update_content(self, text: str, title: str = "Response"):
        self.layout["content"].update(
            Panel(Text.from_ansi(text), title=title)
        )

    def clear_content(self):
        self.content_buffer = ""
        self._update_content("", title="Ready")

    def append_content(self, token: str):
        self.content_buffer += token
        self._update_content(self.content_buffer)

    def set_content(self, text: str, title: str = "Response"):
        self.content_buffer = text
        self._update_content(text, title=title)

    # --- Toolbar ---
    def _update_toolbar(self, status: str, mode: str = "IDLE"):
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)
        grid.add_row(
            f"[bold white]{status}[/]",
            f"[bold yellow]{datetime.now().strftime('%H:%M:%S')}[/]  [bold cyan]{mode}[/]",
        )
        self.layout["toolbar"].update(
            Panel(grid, style="white on #333333", title="Toolbar", height=3)
        )

    def set_toolbar_status(self, status: str, mode: str = "IDLE"):
        self._update_toolbar(status, mode)

    # --- Convenience: stop/start Live around blocking input ---
    def stop(self):
        self.live.stop()

    def start(self):
        self.live.start()
