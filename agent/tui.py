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
        # Current response array.
        # 0 -> thinking starts widget
        # 1 -> thinking body widget
        # 2 -> thinking ends widget
        # 3 -> response body widget
        self.current_response = {}
        self.generating = False
        self.reasoning = False

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

    def _send_user_message(self, text: str) -> None:
        self._add_prompt("user", text)
        self._start_generating(text)

    def _add_prompt(self, role: str, text: str) -> None:
        history = self.query_one("#history", VerticalScroll)
        title = Static(f" ⩥ {role.title()} ⩤ ", classes=f"{role}-title")
        body = Static(text)
        history.mount(title, body)
        history.scroll_end(animate=False)

    def _start_generating(self, prompt) -> None:
        self.generating = True
        
        # Disable input to prevent double submissions
        self.query_one("#input-area", TextArea).disabled = True

        history = self.query_one("#history", VerticalScroll)
        title = Static(" ⩥ Agent ⩤ ", classes="agent-title")
        history.mount(title)

        # Thinking start
        self.current_response[0] = Static("", classes="thinking-header")
        self.current_response[0].styles.display = "none"
        # Thinking content
        self.current_response[1] = Static("", classes="thinking-body")
        self.current_response[1].styles.display = "none"
        # Done thinking
        self.current_response[2] = Static("", classes="thinking-header")
        self.current_response[2].styles.display = "none"
        # Response content
        self.current_response[3] = Static("", classes="response-body")
        self.current_response[3].styles.display = "none"

        # Mount all
        history.mount(self.current_response[0])
        history.mount(self.current_response[1])
        history.mount(self.current_response[2])
        history.mount(self.current_response[3])

        # Helper to scroll history on the UI thread
        def scroll_history():
            pass
            # self.query_one("#history",
            #                VerticalScroll).scroll_end(animate=True,
            #                                           immediate=False,
            #                                           x_axis=False)

        # Callbacks
        def content_callback(text):
            self.app.call_from_thread(self._on_content_update, text)
            self.app.call_from_thread(scroll_history) 

        def reasoning_callback(mode, text=None):
            self.app.call_from_thread(self._on_reasoning_update, mode, text)
            self.app.call_from_thread(scroll_history) 

        # Run the synchronous agent.run in a background thread
        future = self.executor.submit(
                                      self.agent.run,
                                      prompt,
                                      reasoning_callback,
                                      content_callback)

        # Hook into completion to update UI stats and re-enable input
        future.add_done_callback(
            lambda f: self.app.call_from_thread(self._finish_generating, f.result())
        )

    # Reasoning ends
    def _on_reasoning_update(self, mode:str, text:str=None) -> None:
        """Called once when reasoning ends."""
        match mode:
            case 'start':
                # Start reasoning
                reasoning = True
                w = self.current_response[0]
                if w:
                    w.styles.display = "block"
                    w.update(" Thinking...")
            case 'body':
                # Reasoning content
                w = self.current_response[1]
                if w:
                    w.styles.display = "block"
                    current_text = w.content
                    w.update(current_text + text)
            case 'end':
                # End reasoning
                w = self.current_response[2]
                if w:
                    w.styles.display = "block"
                    w.update(" Done thinking")
                reasoning = False
        

    # Content update
    def _on_content_update(self, text:str) -> None:
        """Called incrementally during streaming."""
        w = self.current_response[3]
        if w:
            # Append content
            w.styles.display = "block"
            current_text = w.content
            w.update(current_text + text)

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
