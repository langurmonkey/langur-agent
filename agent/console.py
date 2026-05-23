from rich.console import Console
from rich.traceback import install

# Create console
console = Console()
# Replace default error tracebacks with better version
install()

