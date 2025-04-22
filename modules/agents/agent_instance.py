import logging
import time
import json
import os
from typing import Dict, Any, Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular import issues at runtime
# AgentManager is only needed for type hints within this file.
if TYPE_CHECKING:
    from .agent_manager import AgentManager # Import AgentManager only for type hinting

logger = logging.getLogger(__name__)

class AgentInstance:
    """
    Represents a single, stateful agent instance managed by the AgentManager.
    Contains the agent's specific state, configuration, and core execution logic.
    """

    def __init__(
        self,
        agent_id: str,
        agent_manager: 'AgentManager', # Use forward reference string or TYPE_CHECKING
        agent_type: str = "GenericAgent",
        config: Optional[Dict[str, Any]] = None,
        initial_state: Optional[Dict[str, Any]] = None,
    ):
        """
        Initializes an AgentInstance.

        Args:
            agent_id (str): The unique identifier for this agent.
            agent_manager (AgentManager): Reference to the manager for accessing shared resources.
            agent_type (str): The type or role of the agent (e.g., 'Planner', 'Executor').
            config (Optional[Dict[str, Any]]): Static configuration for the agent.
            initial_state (Optional[Dict[str, Any]]): Initial dynamic state values.
        """
        self.agent_id = agent_id
        self.agent_manager = agent_manager # Store reference to the manager
        self.agent_type = agent_type
        self.config = config if config is not None else {}

        # --- State Initialization ---
        # Default state values
        self.state: Dict[str, Any] = {
            "status": "idle", # e.g., idle, running, paused, finished, error
            "last_run_timestamp": None,
            "run_count": 0,
            "error_count": 0,
            "custom_data": {}, # For agent-specific dynamic data
            # Include config and type in state for saving/loading consistency
            "agent_type": self.agent_type,
            "config": self.config,
        }
        # Merge initial_state if provided, overwriting defaults
        if initial_state:
            # Special handling: Ensure agent_id from state matches provided id
            if "agent_id" in initial_state and initial_state["agent_id"] != self.agent_id:
                 logger.warning(f"Agent {self.agent_id}: Mismatch between provided agent_id and ID in initial_state ('{initial_state['agent_id']}'). Using provided ID.")
            # We don't need to store agent_id within the state dict itself if it's the primary key
            initial_state.pop("agent_id", None) # Remove agent_id if present in state dict

            # Update state, potentially overwriting type/config if they were in the loaded state
            self.state.update(initial_state)
            # Refresh instance attributes from potentially loaded state
            self.agent_type = self.state.get("agent_type", self.agent_type)
            self.config = self.state.get("config", self.config)
            logger.info(f"Agent {self.agent_id}: Initial state loaded and merged.")
        else:
             logger.info(f"Agent {self.agent_id}: Initialized with default state.")


        logger.info(f"AgentInstance initialized: ID={self.agent_id}, Type={self.agent_type}")


    def run(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        The main execution logic for the agent.
        Processes inputs, interacts with tools/memory via AgentManager, updates state.

        Args:
            inputs (Optional[Dict[str, Any]]): Data provided for this specific run.

        Returns:
            Dict[str, Any]: The primary output or result of this agent run.
        """
        start_time = time.time()
        self.state['status'] = 'running'
        self.state['last_run_timestamp'] = start_time
        self.state['run_count'] += 1
        logger.info(f"Agent {self.agent_id} run triggered. Inputs: {inputs}")

        output = {}
        processed_info = "Processed inputs based on config: default" # Default message

        # --- CORRECTED LOGIC: Check inputs and use calculator tool ---
        try:
            task = inputs.get('task') if inputs else None

            if task == 'calculate':
                logger.info(f"Agent {self.agent_id}: Received 'calculate' task. Attempting to use calculator tool.")
                op = inputs.get('op')
                a = inputs.get('a')
                b = inputs.get('b')

                # Basic validation of calculator inputs
                if op and a is not None and b is not None:
                    # Access ToolManager via AgentManager
                    if self.agent_manager and self.agent_manager.tool_manager:
                        # --- Step 1: Get the tool instance ---
                        calculator_tool = self.agent_manager.tool_manager.get_tool("calculator") # <<< USE get_tool

                        if calculator_tool:
                            # --- Step 2: Execute the tool instance ---
                            tool_args = {"operation": op, "operand1": a, "operand2": b}
                            logger.debug(f"Agent {self.agent_id}: Calling calculator tool execute() with args: {tool_args}")
                            tool_result = calculator_tool.execute(tool_args) # <<< CALL execute() ON THE TOOL
                            logger.info(f"Agent {self.agent_id}: Calculator tool result: {tool_result}")

                            # Structure the agent's output based on tool result
                            output = {
                                "message": f"Calculation task '{op}' completed.",
                                "tool_status": tool_result.get("status", "unknown"),
                                "calculation_result": tool_result.get("result"), # Will be None if status is error
                                "error_details": tool_result.get("error_message") # Will be None if status is success
                            }
                            processed_info = f"Executed calculator tool for operation: {op}"
                        else:
                            # Tool not found
                            logger.error(f"Agent {self.agent_id}: Calculator tool not found in ToolManager.")
                            output = {"error": "Calculator tool not registered or available."}
                            self.state['error_count'] += 1
                            processed_info = "Attempted calculation but calculator tool was not found."

                    else:
                        logger.error(f"Agent {self.agent_id}: Cannot execute calculator task. ToolManager not available.")
                        output = {"error": "ToolManager not available"}
                        self.state['error_count'] += 1
                else:
                    logger.warning(f"Agent {self.agent_id}: Incomplete inputs for 'calculate' task: {inputs}")
                    output = {"error": "Missing 'op', 'a', or 'b' for calculate task."}
                    self.state['error_count'] += 1
                    processed_info = "Attempted calculation but inputs were incomplete."

            else:
                # Default processing if task is not 'calculate' or no task provided
                logger.info(f"Agent {self.agent_id}: No specific task handler. Performing default processing.")
                # You might add other task handlers here using elif task == '...'
                output = {
                     "message": f"Agent {self.agent_id} ({self.agent_type}) completed processing.",
                     "processed_info": processed_info,
                     "received_inputs": inputs # Echo inputs if not specifically handled
                }

            self.state['status'] = 'idle' # Set back to idle after successful run

        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Error during run execution: {e}", exc_info=True)
            self.state['status'] = 'error'
            self.state['error_count'] += 1
            output = {"error": f"An unexpected error occurred: {str(e)}"}

        end_time = time.time()
        run_duration = end_time - start_time
        logger.info(f"Agent {self.agent_id} run finished in {run_duration:.2f}s. Status: {self.state['status']}. Output: {output}")

        # --- Save state after run ---
        # Consider if saving state after every run is desired or too frequent
        if self.agent_manager:
             self.agent_manager.save_agent_state(self.agent_id)

        return output


    def get_state(self) -> Dict[str, Any]:
        """Returns the current dynamic state of the agent."""
        # Ensure essential identifiers are part of the returned state for saving
        state_copy = self.state.copy()
        state_copy["agent_id"] = self.agent_id # Add agent_id for saving/reloading context
        state_copy["agent_type"] = self.agent_type
        state_copy["config"] = self.config
        return state_copy

    def load_state(self, state_data: Dict[str, Any]):
        """
        Loads state into the agent, typically used after initialization.
        Be careful about overwriting essential attributes like agent_id or agent_manager.
        """
        # Avoid overwriting critical instance references or the ID itself
        state_data.pop("agent_id", None)
        state_data.pop("agent_manager", None) # Should not be part of saved state anyway

        # Update the agent's state dictionary
        self.state.update(state_data)

        # Refresh instance attributes from the loaded state if necessary
        self.agent_type = self.state.get("agent_type", self.agent_type)
        self.config = self.state.get("config", self.config)

        logger.info(f"Agent {self.agent_id}: State loaded successfully. Current status: {self.state.get('status')}")


    # --- Example methods for interacting with shared resources via manager ---

    def _log_event(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        """Logs an event to the shared structured memory via the AgentManager."""
        if self.agent_manager:
            # Use agent_id as the source
            self.agent_manager.log_event_to_memory(event_type, source=self.agent_id, details=details)
        else:
            logger.warning(f"Agent {self.agent_id}: Cannot log event. AgentManager not available.")

    def _use_tool(self, tool_name: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Uses a tool via the AgentManager's ToolManager."""
        if self.agent_manager and self.agent_manager.tool_manager:
            # --- CORRECTED TOOL USAGE ---
            tool_instance = self.agent_manager.tool_manager.get_tool(tool_name)
            if tool_instance:
                return tool_instance.execute(args)
            else:
                logger.error(f"Agent {self.agent_id}: Tool '{tool_name}' not found in ToolManager.")
                return {"status": "error", "error_message": f"Tool '{tool_name}' not found."}
            # --- END CORRECTION ---
        else:
            logger.error(f"Agent {self.agent_id}: Cannot use tool '{tool_name}'. ToolManager not available.")
            return {"status": "error", "error_message": "ToolManager not available"}

