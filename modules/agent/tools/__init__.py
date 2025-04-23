"""
Agent Tools Submodule Initialization
------------------------------------

This submodule contains tools that agents can use to interact with
external systems or perform specific actions (e.g., file operations,
web browsing, shell commands).

It also provides the ToolManager for discovering and loading these tools.
"""

# Expose the ToolManager as the primary interface for accessing tools
from .tool_manager import ToolManager

# Optionally, expose individual tool classes if they are frequently
# needed for direct instantiation or type hinting elsewhere.
# However, it's often cleaner to access tools via the ToolManager instance.
from .file_tool import FileSystemTool
from .shell_tool import ShellTool
from .web_tool import WebBrowserTool # Assuming this is the class name in web_tool.py

__all__ = [
    "ToolManager",
    "FileSystemTool",
    "ShellTool",
    "WebBrowserTool",
]

