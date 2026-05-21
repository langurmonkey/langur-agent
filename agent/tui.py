from textual import events, on
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.widgets import Header, Static, TextArea
from textual.message import Message

from agent.agent import Agent

class LangurAgent(App):
    CSS_PATH = "../layout/layout.tcss"

    def __init__(self):
        super().__init__()
        self.agent = None
        self.current_response = None
        self.generating = False

    def compose(self) -> ComposeResult:
        yield Static("  [b]Langur Agent[/b]", id="title")
        yield Static("  [b]Ctrl+Q[/b]: quit", id="toolbar")
        yield VerticalScroll(id="history")
        yield Prompt(id="input-bar")

    def on_mount(self) -> None:
        self.agent = Agent()
        self.query_one("#input-area", TextArea).focus()

    def _add_to_history(self, role: str, text: str) -> None:
        history = self.query_one("#history", VerticalScroll)
        title = Static(f" ⩥ {role.title()} ⩤", classes=f"{role}-title")
        body = Static(text)
        history.mount(title, body)
        history.scroll_end(animate=False)

    def _send_user_message(self, text: str) -> None:
        self._add_to_history("user", text)
        self._start_generating(text)

    def _start_generating(self, prompt) -> None:
        self.generating = True
        history = self.query_one("#history", VerticalScroll)
        title = Static(" ⩥ Agent ⩤", classes="agent-title")
        self.current_response = Static("", classes="response")
        history.mount(title, self.current_response)
        self.query_one("#input-area", TextArea).focus()
        self.agent.run(prompt, self._on_response_update)

    def _on_response_update(self, text: str) -> None:
        """Called incrementally during streaming."""
        if self.current_response:
            current_text = self.current_response.content
            self.current_response.update(current_text + text)

    def _finish_generating(self, result) -> None:
        self.generating = False
        if result:
            text, total_tokens, ntools, total_gen_time = result
            # Append stats
            history = self.query_one("#history", VerticalScroll)
            stats = Static(
                f"  ⏱ {total_gen_time:.1f}s  ⏱ {total_tokens} tokens  ⏱ {ntools} tools  ",
                classes="stats"
            )
            history.mount(stats)


class Prompt(Static):
    """ The prompt """
    def compose(self):
        self.textarea = TextArea(id="input-area", tab_behavior="indent")
        with Vertical():
            yield Static(" [bold][$secondary]Ctrl[/$secondary][/bold]+[bold][$secondary]Enter[/$secondary][/bold]: submit prompt")
            yield self.textarea

    def _on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+enter":
            text = self.textarea.text.strip()
            if text:
                self.textarea.clear()
                self.app._send_user_message(text)
                 
            event.prevent_default()
            return
        # Let all other keys pass through normally (including Enter → newline)
        super()._on_key(event)

if __name__ == "__main__":
    app = LangurAgent()
    app.run()
