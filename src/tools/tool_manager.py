"""
Tool Manager for CPAS3
Discovers, loads, and provides access to tools
"""
import os
import importlib
import inspect
import logging
import pkgutil
from typing import Dict, List, Optional, Type, Any, Callable

from langchain.tools import BaseTool, tool

logger = logging.getLogger(__name__)

class ToolManager:
    """
    Manages the registration, discovery, and execution of tools available to agents.
    """

    def __init__(self, tool_dirs: Optional[List[str]] = None):
        """
        Initialize the Tool Manager
        
        Args:
            tool_dirs (Optional[List[str]]): List of directories to search for tools
                If None, defaults to src/tools
        """
        self._tools: Dict[str, BaseTool] = {}
        
        # Default tool directories
        if tool_dirs is None:
            # Look in the src/tools directory by default
            base_dir = os.path.dirname(os.path.abspath(__file__))
            tool_dirs = [base_dir]
        
        self.tool_dirs = tool_dirs
        
        # Auto-discover tools
        self._discover_tools()
        
        logger.info(f"ToolManager initialized with {len(self._tools)} tools")
    
    def _discover_tools(self):
        """Automatically discover and register tools in the specified directories"""
        for tool_dir in self.tool_dirs:
            if not os.path.exists(tool_dir) or not os.path.isdir(tool_dir):
                logger.warning(f"Tool directory not found: {tool_dir}")
                continue
            
            logger.debug(f"Searching for tools in {tool_dir}")
            
            # Find all Python modules in the directory
            for _, module_name, is_pkg in pkgutil.iter_modules([tool_dir]):
                # Skip the current file and non-tool files
                if module_name == 'tool_manager' or not module_name.endswith('_tool'):
                    continue
                
                try:
                    # Import the module
                    module_path = f"src.tools.{module_name}"
                    module = importlib.import_module(module_path)
                    
                    # Look for BaseTool subclasses or @tool decorated functions
                    for name, obj in inspect.getmembers(module):
                        # Register BaseTool subclasses
                        if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool:
                            logger.debug(f"Found tool class: {name}")
                            try:
                                instance = obj()
                                self.register_tool(instance)
                            except Exception as e:
                                logger.error(f"Error instantiating tool class {name}: {e}")
                        
                        # Register @tool decorated functions
                        elif callable(obj) and hasattr(obj, '_type') and obj._type == 'tool':
                            logger.debug(f"Found tool function: {name}")
                            try:
                                self.register_tool(obj)
                            except Exception as e:
                                logger.error(f"Error registering tool function {name}: {e}")
                
                except Exception as e:
                    logger.error(f"Error importing module {module_name}: {e}")
    
    def register_tool(self, tool_instance: BaseTool):
        """
        Register a tool instance
        
        Args:
            tool_instance (BaseTool): The tool instance to register
        """
        if not isinstance(tool_instance, BaseTool):
            logger.error(f"Attempted to register invalid tool type: {type(tool_instance)}. Must inherit from BaseTool.")
            return

        tool_name = tool_instance.name
        if tool_name in self._tools:
            logger.warning(f"Tool '{tool_name}' is already registered. Overwriting.")
        self._tools[tool_name] = tool_instance
        logger.info(f"Tool registered: '{tool_name}'")
    
    def register_tool_class(self, tool_class: Type[BaseTool], *args, **kwargs):
        """
        Register a tool class by instantiating it
        
        Args:
            tool_class (Type[BaseTool]): The tool class to register
            *args: Positional arguments for instantiation
            **kwargs: Keyword arguments for instantiation
        """
        if not issubclass(tool_class, BaseTool):
            logger.error(f"Attempted to register invalid tool class: {tool_class.__name__}. Must inherit from BaseTool.")
            return

        try:
            instance = tool_class(*args, **kwargs)
            self.register_tool(instance)
        except Exception as e:
            logger.error(f"Failed to instantiate and register tool class {tool_class.__name__}: {e}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name
        
        Args:
            tool_name (str): The name of the tool to retrieve
            
        Returns:
            Optional[BaseTool]: The tool if found, None otherwise
        """
        return self._tools.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all registered tools
        
        Returns:
            List[BaseTool]: List of all registered tools
        """
        return list(self._tools.values())
    
    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """
        Get descriptions of all tools suitable for LLM consumption
        
        Returns:
            List[Dict[str, Any]]: List of tool descriptions
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": getattr(tool, "args_schema", {})
            }
            for tool in self._tools.values()
        ]
