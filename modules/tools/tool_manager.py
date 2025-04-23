import os
import importlib
import inspect
import logging
from typing import Dict, List, Optional, Type, Any
from .base_tool import BaseTool

logger = logging.getLogger(__name__)

class ToolManager:
    """
    Manages the discovery, loading, and access of agent tools.
    Tools are discovered from the same directory as this manager.
    Allows passing configuration arguments during tool instantiation.
    """
    def __init__(
        self,
        tool_directory: Optional[str] = None,
        tool_config: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        if tool_directory is None:
            self.tool_directory = os.path.dirname(os.path.abspath(__file__))
        else:
            self.tool_directory = tool_directory

        self.tool_config = tool_config if tool_config else {}
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        logger.info(f"ToolManager initialized. Scanning directory: {self.tool_directory}")
        logger.debug(f"Tool configurations provided: {self.tool_config}")
        logger.debug(f"BaseTool used for checks: {BaseTool} from {inspect.getfile(BaseTool)}")
        self.discover_and_load_tools()

    def discover_and_load_tools(self):
        """
        Discovers tool classes in the tool directory, instantiates them with
        provided configuration, and registers them.
        """
        logger.info(f"Discovering tools in: {self.tool_directory}")
        discovered_count = 0
        loaded_count = 0

        try:
            logger.debug(f"Files in tool directory: {os.listdir(self.tool_directory)}")
            for filename in os.listdir(self.tool_directory):
                logger.debug(f"Processing file: {filename}")
                if filename.endswith("_tool.py") and not filename.startswith("__"):
                    module_name = filename[:-3] # e.g., 'calculator_tool'

                    # --- CORRECTED PATH CALCULATION ---
                    # Assumes the script is run from the project root (e.g., CPAS3)
                    # and the 'modules' directory is directly under it.
                    # We want a path like 'modules.tools.calculator_tool'
                    package_name = os.path.basename(self.tool_directory) # 'tools'
                    parent_package_name = os.path.basename(os.path.dirname(self.tool_directory)) # 'modules'
                    full_module_path = f"{parent_package_name}.{package_name}.{module_name}"
                    # --- END CORRECTION ---

                    logger.debug(f"Calculated module path: {full_module_path}")

                    try:
                        logger.debug(f"Attempting to import module: {full_module_path}")
                        module = importlib.import_module(full_module_path)
                        logger.debug(f"Successfully imported module: {full_module_path}")

                        logger.debug(f"Inspecting members of module: {module_name}")
                        members = inspect.getmembers(module)
                        logger.debug(f"Found {len(members)} members in {module_name}")

                        for name, obj in members:
                            logger.debug(f"Checking member: name='{name}', type='{type(obj)}'")
                            if inspect.isclass(obj):
                                logger.debug(f"Member '{name}' is a class.")
                                try:
                                    # Add a check if obj is BaseTool itself before issubclass
                                    is_base_tool_itself = (obj is BaseTool)
                                    logger.debug(f"Is '{name}' the BaseTool itself? {is_base_tool_itself}")
                                    if is_base_tool_itself:
                                        logger.debug(f"Skipping class '{name}': Is BaseTool itself.")
                                        continue # Skip BaseTool itself

                                    # Check inheritance - wrap in try-except for robustness
                                    is_subclass = issubclass(obj, BaseTool)
                                    logger.debug(f"Is '{name}' a subclass of {BaseTool}? {is_subclass}")

                                    if is_subclass:
                                        if name not in self._tool_classes:
                                            self._tool_classes[name] = obj
                                            logger.info(f"Discovered tool class: {name} in {filename}")
                                            discovered_count += 1

                                            try:
                                                tool_specific_config = self.tool_config.get(name, {})
                                                logger.debug(f"Attempting to instantiate {name} with config: {tool_specific_config}")
                                                instance = obj(**tool_specific_config)
                                                logger.debug(f"Successfully instantiated {name}")

                                                tool_instance_name = instance.name
                                                if tool_instance_name in self._tools:
                                                    logger.warning(f"Tool name '{tool_instance_name}' from class {name} conflicts. Overwriting.")
                                                self._tools[tool_instance_name] = instance
                                                logger.info(f"Successfully loaded and registered tool: '{tool_instance_name}' (from class {name})")
                                                loaded_count += 1
                                            except TypeError as te:
                                                 logger.error(f"TypeError instantiating {name} from {filename}. Check __init__ args/config. Config: {tool_specific_config}. Error: {te}", exc_info=True)
                                            except Exception as e:
                                                 logger.error(f"Failed to instantiate/register tool class {name} from {filename}: {e}", exc_info=True)
                                    else:
                                         logger.debug(f"Skipping class '{name}': Not a valid subclass of BaseTool.")

                                except TypeError as e:
                                     # issubclass can raise TypeError if obj is not a class (though we check inspect.isclass)
                                     logger.warning(f"Could not perform issubclass check on '{name}': {e}")
                            else:
                                 logger.debug(f"Skipping member '{name}': Not a class.")


                    except ImportError as e:
                        logger.error(f"Failed to import module {full_module_path}: {e}", exc_info=True)
                    except Exception as e:
                        logger.error(f"Error processing file {filename} or its contents: {e}", exc_info=True)
                else:
                    logger.debug(f"Skipping file (doesn't match pattern or is __init__): {filename}")


        except FileNotFoundError:
            logger.error(f"Tool directory not found: {self.tool_directory}")
        except Exception as e:
            logger.error(f"Failed during tool discovery: {e}", exc_info=True)

        logger.info(f"Tool discovery complete. Discovered {discovered_count} classes, loaded {loaded_count} instances.")

    # --- Rest of the ToolManager class remains the same ---
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        tool = self._tools.get(tool_name)
        return tool

    def get_all_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def list_tools(self) -> List[Dict[str, Any]]:
        tool_list = []
        for name, tool in self._tools.items():
            try:
                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                }
                tool_list.append(tool_schema)
            except Exception as e:
                logger.error(f"Failed to get schema for tool '{name}': {e}", exc_info=True)
        return tool_list

    def use_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        tool = self.get_tool(tool_name)
        if not tool:
            logger.error(f"Tool '{tool_name}' not found for execution.")
            return {"status": "error", "error_message": f"Tool '{tool_name}' not found."}
        try:
            logger.info(f"Executing tool '{tool_name}' with args: {kwargs}")
            result = tool.execute(**kwargs)
            logger.info(f"Tool '{tool_name}' execution finished. Result status: {result.get('status', 'N/A')}")
            if not isinstance(result, dict):
                 logger.error(f"Tool '{tool_name}' execute method did not return a dictionary. Returned: {type(result)}")
                 return {"status": "error", "error_message": f"Tool '{tool_name}' returned an invalid result type."}
            if 'status' not in result:
                logger.warning(f"Tool '{tool_name}' result dict missing 'status' key. Assuming 'success'.")
                result['status'] = 'success'
            return result
        except Exception as e:
            logger.error(f"Error during execution of tool '{tool_name}': {e}", exc_info=True)
            return {"status": "error", "error_message": f"An unexpected error occurred executing tool '{tool_name}': {str(e)}"}

