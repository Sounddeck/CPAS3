"""
Tool registry for CPAS agents
"""
from modules.agent.tools.file_system_tool import FileSystemTool

# Dictionary of available tools
available_tools = {
    "file_system_tool": FileSystemTool
}

def get_tool_instance(tool_id):
    """Get a tool instance by ID"""
    tool_class = available_tools.get(tool_id)
    if tool_class:
        return tool_class()
    return None

def list_available_tools():
    """List all available tools"""
    return list(available_tools.keys())
