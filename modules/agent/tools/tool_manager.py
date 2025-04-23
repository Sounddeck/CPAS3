import os
import importlib
import inspect
import logging
from typing import List, Dict, Type, Optional, Any

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

class ToolManager:
    """
    Manages the discovery, loading, and access of agent tools.
    Tools are discovered from the same directory as this manager.
    Allows passing configuration arguments during tool instantiation.
    """
    def __init__(self, tool_directory: Optional[str] = None, tool_config: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initializes the ToolManager.

        Args:
            tool_directory: The directory to scan for tool files. Defaults to the directory
                            containing this tool_manager.py file.
            tool_config: A dictionary where keys are tool class names (e.g., "FileTool")
                         and values are dictionaries of arguments to pass to the tool's
                         __init__ method (e.g., {"FileTool": {"base_dir": "/path/to/workspace"}}).
        """
        if tool_directory is None:
            self.tool_directory = os.path.dirname(os.path.abspath(__file__))
        else:
            self.tool_directory = tool_directory

        self.tool_config = tool_config if tool_config else {}
        self._tools: Dict[str, BaseTool] = {} # Stores instantiated tools by name
        self._tool_classes: Dict[str, Type[BaseTool]] = {} # Stores discovered tool classes by class name
        logger.info(f"ToolManager initialized. Scanning directory: {self.tool_directory}")
        logger.debug(f"Tool configurations provided: {self.tool_config}")
        self.discover_tools()

    def discover_tools(self):
        """
        Discovers tool classes in the tool directory, instantiates them with configuration,
        and stores them.
        """
        self._tools = {}
        self._tool_classes = {}
        logger.debug(f"Scanning for tools in {self.tool_directory}...")

        for filename in os.listdir(self.tool_directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module_path = f".{module_name}" # Relative import from within the tools package

                try:
                    # Import the module relative to the 'tools' package
                    module = importlib.import_module(module_path, package=__package__)

                    for name, obj in inspect.getmembers(module):
                        # Check if it's a class, is defined in this module (not imported),
                        # inherits from BaseTool, and is not BaseTool itself.
                        if inspect.isclass(obj) and \
                           obj.__module__ == module.__name__ and \
                           issubclass(obj, BaseTool) and \
                           obj is not BaseTool:

                            logger.debug(f"Discovered tool class '{name}' in {filename}")
                            self._tool_classes[name] = obj

                            # --- Instantiation with Configuration ---
                            try:
                                tool_instance: Optional[BaseTool] = None
                                class_config = self.tool_config.get(name, {}) # Get config for this class name
                                logger.debug(f"Attempting instantiation of {name} with config: {class_config}")

                                # Instantiate the tool, passing the specific config if provided
                                tool_instance = obj(**class_config)

                                if tool_instance and hasattr(tool_instance, 'name'):
                                     if tool_instance.name in self._tools:
                                          logger.warning(f"Duplicate tool name '{tool_instance.name}' found from class {name}. Overwriting.")
                                     self._tools[tool_instance.name] = tool_instance
                                     logger.info(f"Successfully loaded and instantiated tool: {tool_instance.name} (from class {name})")
                                else:
                                     logger.warning(f"Could not instantiate tool from class {name} or it lacks a 'name' attribute.")

                            except TypeError as e:
                                logger.error(f"Failed to instantiate tool class '{name}'. Check __init__ arguments and provided config. Error: {e}", exc_info=True)
                            except Exception as e:
                                logger.error(f"Unexpected error instantiating tool class '{name}': {e}", exc_info=True)
                            # --- End Instantiation ---

                except ImportError as e:
                    logger.error(f"Failed to import module {module_name} from {filename}: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error processing file {filename}: {e}", exc_info=True)

        logger.info(f"Tool discovery complete. Found {len(self._tools)} usable tools.")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Returns the instantiated tool with the given name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """Returns a list of all instantiated tools."""
        return list(self._tools.values())

    def get_tool_class(self, class_name: str) -> Optional[Type[BaseTool]]:
        """Returns the discovered tool class with the given class name."""
        return self._tool_classes.get(class_name)

    def get_all_tool_classes(self) -> Dict[str, Type[BaseTool]]:
        """Returns a dictionary of all discovered tool classes."""
        return self._tool_classes

