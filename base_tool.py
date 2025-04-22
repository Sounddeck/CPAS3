import logging
from typing import Dict, List, Optional, Type, Any # Make sure Any is imported
from .base_tool import BaseTool # Relative import for BaseTool

logger = logging.getLogger(__name__)

class ToolManager:
    """
    Manages the registration, discovery, and execution of tools available to agents.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        logger.info("ToolManager initialized.")

    def register_tool(self, tool_instance: BaseTool):
        """
        Registers an instance of a tool.

        Args:
            tool_instance (BaseTool): An initialized instance of a class derived from BaseTool.
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
        Registers a tool by providing its class and initialization arguments.

        Args:
            tool_class (Type[BaseTool]): The class of the tool to register (must inherit from BaseTool).
            *args: Positional arguments to pass to the tool's constructor.
            **kwargs: Keyword arguments to pass to the tool's constructor.
        """
        if not issubclass(tool_class, BaseTool):
             logger.error(f"Attempted to register invalid tool class: {tool_class.__name__}. Must inherit from BaseTool.")
             return

        try:
             instance = tool_class(*args, **kwargs)
             self.register_tool(instance)
        except Exception as e:
             logger.error(f"Failed to instantiate and register tool class {tool_class.__name__}: {e}", exc_info=True)


    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Retrieves a registered tool instance by its name.

        Args:
            tool_name (str): The name of the tool to retrieve.

        Returns:
            Optional[BaseTool]: The tool instance if found, otherwise None.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            logger.warning(f"Attempted to access unregistered tool: '{tool_name}'")
        return tool

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Provides a list of available tools with their names, descriptions, and parameters,
        suitable for presenting to an agent (e.g., an LLM).

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each describing a tool.
        """
        tool_list = []
        for name, tool in self._tools.items():
            try:
                # Ensure properties exist before accessing
                tool_name = getattr(tool, 'name', 'Unknown Name')
                tool_description = getattr(tool, 'description', 'No description provided.')
                tool_parameters = getattr(tool, 'parameters', []) # Default to empty list

                tool_list.append({
                    "name": tool_name,
                    "description": tool_description,
                    "parameters": tool_parameters, # Include parameter details
                })
            except Exception as e:
                logger.error(f"Failed to get details for tool '{name}': {e}", exc_info=True)
        return tool_list

    def use_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a specified tool with the given arguments after validation.

        Args:
            tool_name (str): The name of the tool to execute.
            args (Dict[str, Any]): The arguments to pass to the tool's execute method.

        Returns:
            Dict[str, Any]: The result dictionary from the tool's execute method,
                            or an error dictionary if the tool is not found, validation fails,
                            or execution fails.
        """
        tool = self.get_tool(tool_name)
        if not tool:
            logger.error(f"Tool '{tool_name}' not found.") # Log error here too
            return {"status": "error", "error_message": f"Tool '{tool_name}' not found."}

        # Validate arguments before execution
        try:
            if not tool.validate_args(args):
                 # Errors should be logged within validate_args
                 logger.error(f"Invalid arguments provided for tool '{tool_name}'. Args: {args}")
                 return {"status": "error", "error_message": f"Invalid arguments provided for tool '{tool_name}'."}
        except Exception as e:
             logger.error(f"Error during argument validation for tool '{tool_name}': {e}", exc_info=True)
             return {"status": "error", "error_message": f"Error validating arguments for tool '{tool_name}': {str(e)}"}


        # Execute the tool
        try:
            logger.info(f"Executing tool '{tool_name}' with args: {args}")
            result = tool.execute(args)
            logger.info(f"Tool '{tool_name}' execution finished. Result status: {result.get('status', 'N/A')}")

            # Ensure result is a dictionary and has a status
            if not isinstance(result, dict):
                 logger.error(f"Tool '{tool_name}' execute method did not return a dictionary. Returned: {type(result)}")
                 return {"status": "error", "error_message": f"Tool '{tool_name}' returned an invalid result type."}

            if 'status' not in result:
                logger.warning(f"Tool '{tool_name}' result dict missing 'status' key. Assuming 'success' based on lack of exception.")
                # Decide on default status, e.g., assume success if no error?
                result['status'] = 'success' # Or maybe 'unknown'

            return result
        except Exception as e:
            logger.error(f"Error during execution of tool '{tool_name}': {e}", exc_info=True)
            return {"status": "error", "error_message": f"An unexpected error occurred while executing tool '{tool_name}': {str(e)}"}

