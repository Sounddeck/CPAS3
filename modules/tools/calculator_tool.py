import logging
from typing import Dict, Any, List
from .base_tool import BaseTool

logger = logging.getLogger(__name__)

class CalculatorTool(BaseTool):
    """
    A simple calculator tool that performs basic arithmetic operations.
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Performs basic arithmetic operations: add, subtract, multiply, divide."

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'operation',
                'type': 'string',
                'description': 'The operation to perform (add, subtract, multiply, divide).',
                'required': True
            },
            {
                'name': 'operand1',
                'type': 'float', # Use float to handle decimals and integers
                'description': 'The first number for the operation.',
                'required': True
            },
            {
                'name': 'operand2',
                'type': 'float', # Use float to handle decimals and integers
                'description': 'The second number for the operation.',
                'required': True
            }
        ]

    def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the calculation based on the provided arguments.

        Args:
            args (Dict[str, Any]): Dictionary with 'operation', 'operand1', 'operand2'.

        Returns:
            Dict[str, Any]: Dictionary with 'status' and 'result' or 'error_message'.
        """
        tool_name = self.name # Get tool name for logging/errors
        logger.debug(f"Executing tool '{tool_name}' with args: {args}")

        # --- Argument Validation ---
        if not self.validate_args(args):
            # validate_args logs the specific error
            return {"status": "error", "error_message": f"Invalid arguments provided to tool '{tool_name}'."}

        # --- Extract validated arguments ---
        # We know they exist and should be of the correct type (or convertible like int to float)
        # based on validate_args passing.
        operation = args.get('operation', '').lower() # Use .get for safety, though required check done
        try:
            # Convert operands to float for calculation
            operand1 = float(args['operand1'])
            operand2 = float(args['operand2'])
        except (ValueError, TypeError) as e:
            # This should theoretically not happen if validate_args is correct, but good failsafe
            logger.error(f"Tool '{tool_name}': Error converting operands to float after validation: {e}", exc_info=True)
            return {"status": "error", "error_message": f"Tool '{tool_name}': Invalid numeric value provided for operands."}
        except KeyError as e:
             # This should not happen due to required check in validate_args
             logger.error(f"Tool '{tool_name}': Missing operand key '{e}' after validation.", exc_info=True)
             return {"status": "error", "error_message": f"Tool '{tool_name}': Missing required operand '{e}'."}


        # --- Perform Calculation ---
        result: Optional[float] = None # Use Optional for type hinting
        error_message: Optional[str] = None

        try:
            if operation == 'add':
                result = operand1 + operand2
            elif operation == 'subtract':
                result = operand1 - operand2
            elif operation == 'multiply':
                result = operand1 * operand2
            elif operation == 'divide':
                if operand2 == 0:
                    logger.warning(f"Tool '{tool_name}': Division by zero attempted.")
                    error_message = "Division by zero is not allowed."
                else:
                    result = operand1 / operand2
            else:
                logger.warning(f"Tool '{tool_name}': Invalid operation '{operation}' requested.")
                error_message = f"Unsupported operation: '{args.get('operation')}'. Use add, subtract, multiply, or divide."

            # --- Format Response ---
            if error_message:
                logger.error(f"Tool '{tool_name}' execution failed: {error_message}")
                return {"status": "error", "error_message": error_message}
            elif result is not None:
                 # Format result nicely (e.g., handle integer results cleanly)
                 formatted_result = int(result) if result.is_integer() else result
                 logger.info(f"Tool '{tool_name}' executed successfully. Result: {formatted_result}")
                 return {"status": "success", "result": formatted_result}
            else:
                 # Should not happen if logic is correct
                 logger.error(f"Tool '{tool_name}': Calculation resulted in None without error message.")
                 return {"status": "error", "error_message": f"Tool '{tool_name}': Unexpected calculation state."}

        except Exception as e:
            # Catch any unexpected errors during calculation itself
            logger.error(f"Tool '{tool_name}': Unexpected error during operation execution: {e}", exc_info=True)
            # --- CORRECTED LINE 141 ---
            return {"status": "error", "error_message": f"An unexpected error occurred while executing tool '{tool_name}': {str(e)}"}
