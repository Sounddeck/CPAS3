import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """
    Abstract Base Class for all tools available to agents.
    Ensures tools have a consistent interface for discovery and execution.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """A unique, programmatic name for the tool (e.g., 'web_search', 'file_reader')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A human-readable description of what the tool does and its purpose."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[Dict[str, Any]]:
        """
        A list describing the parameters the tool's execute method expects.
        Each item in the list should be a dictionary detailing a parameter:
        {
            'name': 'param_name',
            'type': 'string | integer | boolean | float | list | dict',
            'description': 'What this parameter is for.',
            'required': True | False
        }
        """
        pass

    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the tool's core logic.

        Args:
            args (Dict[str, Any]): A dictionary containing the arguments for execution,
                                   matching the structure defined in 'parameters'.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the execution.
                            Should ideally include a 'status' (e.g., 'success', 'error')
                            and 'result' or 'error_message'.
        """
        pass

    def validate_args(self, args: Dict[str, Any]) -> bool:
        """
        Validates the provided arguments against the tool's defined parameters.
        Basic implementation provided, can be overridden for more complex validation.

        Args:
            args (Dict[str, Any]): The arguments to validate.

        Returns:
            bool: True if arguments are valid, False otherwise. Logs errors on failure.
        """
        required_params = {p['name'] for p in self.parameters if p.get('required', False)}
        provided_params = set(args.keys())
        param_details = {p['name']: p for p in self.parameters}

        # Check for missing required parameters
        missing = required_params - provided_params
        if missing:
            logger.error(f"Tool '{self.name}': Missing required parameters: {missing}")
            return False

        # Check for unexpected parameters (optional, can be strict or lenient)
        # allowed_params = {p['name'] for p in self.parameters}
        # extra = provided_params - allowed_params
        # if extra:
        #     logger.warning(f"Tool '{self.name}': Received unexpected parameters: {extra}")
        #     # Decide if this should be an error or just a warning
        #     # return False

        # Basic type checking (can be expanded)
        for name, value in args.items():
            details = param_details.get(name)
            if details:
                expected_type_str = details.get('type', 'any')
                # Basic type mapping - needs refinement for complex types like list, dict
                type_map = {'string': str, 'integer': int, 'boolean': bool, 'float': float, 'list': list, 'dict': dict}
                expected_type = type_map.get(expected_type_str)

                # Perform the type check (This is where lines ~78-82 are)
                if expected_type and not isinstance(value, expected_type):
                    # Special case: Allow integers if a float is expected
                    if not (expected_type is float and isinstance(value, int)): # <<< Line ~78: Note: NO 'try:' here
                        logger.error(f"Tool '{self.name}': Parameter '{name}' expected type '{expected_type_str}', got '{type(value).__name__}'") # <<< Line ~79: Correctly indented
                        return False # <<< Line ~80: Correctly indented
            # else: # This case handled by 'extra' check above if enabled

        # If all checks pass
        return True

