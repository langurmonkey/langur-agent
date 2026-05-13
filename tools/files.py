"""File listing, reading, and writing tools.

Allows the agent to operate with files and directories in the file system.
"""

import os
from agent.tools import register_tool

def read_file_handler(args):
    """Read a file and return its content."""
    path = args.get("path", "")

    if not path:
        return {"error": "No file path provided"}

    # Expand ~ and relative paths
    path = os.path.expanduser(path)
    path = os.path.abspath(path)

    if not os.path.exists(path):
        return {"error": f"The file does not exist: {path}"}

    if not os.path.isfile(path):
        return {"error": f"The path exists but does not point to a file: {path}"}

    with open(path, "r") as file:
        content = file.read()
        output = {
            "path": path,
            "content": content
        }
        return output

def list_dir_handler(args):
    """List contents of a directory."""
    path = args.get("path", "")

    if not path:
        return {"error": "No path provided"}

    # Expand ~ and relative paths
    path = os.path.expanduser(path)
    path = os.path.abspath(path)

    if not os.path.exists(path):
        return {"error": f"The directory does not exist: {path}"}

    if os.path.isfile(path):
        return {"error": f"The path exists but does not point to a directory: {path}"}

    content = os.listdir(path)
    # Format as a readable listing
    dirs = [f for f in content if os.path.isdir(os.path.join(path, f))]
    files = [f for f in content if os.path.isfile(os.path.join(path, f))]
    lines = []
    if dirs:
        lines.append(f"Directories ({len(dirs)}):")
        for d in sorted(dirs):
            lines.append(f"  📁 {d}/")
    if files:
        lines.append(f"Files ({len(files)}):")
        for f in sorted(files):
            lines.append(f"  📄 {f}")

    return {
        "path": path,
        "content": "\n".join(lines) if lines else "(empty directory)",
        "dirs": dirs,
        "files": files,
    }

register_tool(
    name="read_file",
    description=(
        "Read the full contents of a file. Use this when the user asks to "
        "see file contents, check a file's content, or read any file. "
        "Takes a 'path' argument (absolute or relative path to the file)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The file path to read (e.g., '/home/user/file.txt')",
            },
        },
        "required": ["path"],
    },
    handler=read_file_handler,
)

register_tool(
    name="list_dir",
    description=(
        "List all files and subdirectories in a directory. Use this when the "
        "user asks to see what's in a folder, list directory contents, or "
        "explore a directory structure. Takes a 'path' argument (absolute or "
        "relative path to the directory)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The directory path to list (e.g., '/home/user/projects')",
            },
        },
        "required": ["path"],
    },
    handler=list_dir_handler,
)
