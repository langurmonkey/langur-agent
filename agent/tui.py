import concurrent.futures
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
        self.executor = None  # Store executor instance
        self.current_response = None
        self.current_reasoning = None
        self.generating = False

    def compose(self) -> ComposeResult:
        yield Static("  [b]Langur Agent[/b]", id="title")
        yield Static("  [b]Ctrl+Q[/b]: quit", id="toolbar")
        yield VerticalScroll(id="history")
        yield Prompt(id="input-bar")

    def on_mount(self) -> None:
        self.agent = Agent()
        # Initialize thread pool with 1 worker to prevent overlapping requests
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.query_one("#input-area", TextArea).focus()

    def on_unmount(self) -> None:
        # Clean up the executor
        if self.executor:
            self.executor.shutdown(wait=False)

    def _add_to_history(self, role: str, text: str) -> None:
        history = self.query_one("#history", VerticalScroll)
        title = Static(f" ⩥ {role.title()} ⩤ ", classes=f"{role}-title")
        body = Static(text)
        history.mount(title, body)
        history.scroll_end(animate=False)

    def _send_user_message(self, text: str) -> None:
        self._add_to_history("user", text)
        self._start_generating(text)

    def _start_generating(self, prompt) -> None:
        self.generating = True
        
        # Disable input to prevent double submissions
        self.query_one("#input-area", TextArea).disabled = True

        history = self.query_one("#history", VerticalScroll)
        title = Static(" ⩥ Agent ⩤ ", classes="agent-title")
        history.mount(title)

        self.current_response = Static("", classes="response")
        history.mount(self.current_response)
        self.current_reasoning = None

        # Helper to scroll history on the UI thread
        def scroll_history():
            self.query_one("#history",
                           VerticalScroll).scroll_end(animate=True,
                                                      immediate=False,
                                                      x_axis=False)

        # Callbacks
        def content_callback(text):
            self.app.call_from_thread(self._on_content_update, text)
            self.app.call_from_thread(scroll_history) 

        def reasoning_start_callback(text):
            self.app.call_from_thread(self._on_reasoning_start, text)
            self.app.call_from_thread(scroll_history) 

        def reasoning_callback(text):
            self.app.call_from_thread(self._on_reasoning_update, text)
            self.app.call_from_thread(scroll_history) 

        def reasoning_end_callback(text):
            self.app.call_from_thread(self._on_reasoning_end, text)
            self.app.call_from_thread(scroll_history) 

        # Run the synchronous agent.run in a background thread
        future = self.executor.submit(
                                      self.agent.run,
                                      prompt,
                                      content_callback)

        # Hook into completion to update UI stats and re-enable input
        future.add_done_callback(
            lambda f: self.app.call_from_thread(self._finish_generating, f.result())
        )

    # Reasoning starts
    def _on_reasoning_start(self, text: str) -> None:
        """Called once when reasoning starts."""
        history = self.query_one("#history", VerticalScroll)
        thinking = Static(" Thinking... ", classes="agent-title")
        self.current_reasoning = Static("", classes="response")
        self.current_reasoning.styles.color = "dim"
        history.mount(thinking, self.current_reasoning)

    # Reasoning update
    def _on_reasoning_update(self, text: str) -> None:
        """Called incrementally during reasoning."""
        if self.current_reasoning:
            current_text = self.current_reasoning.content
            self.current_reasoning.update(current_text + text)

    # Reasoning ends
    def _on_reasoning_end(self, text: str) -> None:
        """Called once when reasoning ends."""
        # Stop reasoning, add end
        history = self.query_one("#history", VerticalScroll)
        thinking_end = Static(" Thinking done ", classes="agent-title")
        history.mount(thinking_end)
        # Do NOT create a new response widget here — it was already created upfront.

    # Content update
    def _on_content_update(self, text: str) -> None:
        """Called incrementally during streaming."""
        if self.current_response:
            current_text = self.current_response.content
            self.current_response.update(current_text + text)

    def _finish_generating(self, result) -> None:
        """ Called when generation is done. """
        self.generating = False
        
        # Re-enable input
        self.query_one("#input-area", TextArea).disabled = False
        self.query_one("#input-area", TextArea).focus()

        if result:
            text, total_tokens, ntools, total_gen_time = result
            # Append stats
            history = self.query_one("#history", VerticalScroll)
            stats = Static(
                f"  \u23f1 {total_gen_time:.1f}s  \u23f1 {total_tokens} tokens  \u23f1 {ntools} tools  ",
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
