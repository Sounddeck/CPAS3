import logging
import os
import json
import uuid
from typing import Dict, Optional, Any, Type

# --- Core component imports ---
from modules.memory.structured_memory import StructuredMemory
# --- Tool imports ---
from modules.tools.tool_manager import ToolManager
from modules.tools.calculator_tool import CalculatorTool
# --- Agent instance import ---
# Import AgentInstance only when needed for type hints or instance creation
# to potentially help with complex import scenarios, though the TYPE_CHECKING fix
# in agent_instance.py should have resolved the main circular dependency.
from .agent_instance import AgentInstance


logger = logging.getLogger(__name__)

DEFAULT_AGENT_STATE_DIR = os.path.join(os.path.expanduser("~"), ".cpas3", "agents")
DEFAULT_MEMORY_DB_PATH = os.path.join(os.path.expanduser("~"), ".cpas3", "cpas_memory.db")


class AgentManager:
    """
    Manages the lifecycle, state, and interactions of multiple agent instances.
    Provides access to shared resources like memory and tools.
    """

    def __init__(
        self,
        agent_state_dir: str = DEFAULT_AGENT_STATE_DIR, # <<< PARAMETER DEFINED HERE
        memory_db_path: str = DEFAULT_MEMORY_DB_PATH,   # <<< PARAMETER DEFINED HERE
    ):
        """
        Initializes the AgentManager.

        Args:
            agent_state_dir (str): Directory to store/load agent state files.
            memory_db_path (str): Path to the structured memory database file.
        """
        self.agent_state_dir = agent_state_dir
        self.memory_db_path = memory_db_path
        self.agents: Dict[str, AgentInstance] = {}

        # Ensure the agent state directory exists
        try:
            os.makedirs(self.agent_state_dir, exist_ok=True)
            logger.info(f"Agent state storage initialized at: {self.agent_state_dir}")
        except OSError as e:
            logger.error(f"Failed to create agent state directory {self.agent_state_dir}: {e}", exc_info=True)
            # Decide how to handle this - maybe raise the exception?
            # For now, log the error and continue, state saving/loading will fail.

        # --- Initialize Structured Memory ---
        try:
            self.memory = StructuredMemory(db_path=self.memory_db_path)
            if self.memory.conn: # Check if connection was successful
                 logger.info(f"Structured Memory initialized at: {self.memory_db_path}")
            else:
                 logger.error("Failed to initialize Structured Memory. Memory operations will not work.")
                 # Set memory to None or a dummy object to prevent errors later?
                 self.memory = None # Or implement a NoOpMemory class
        except Exception as e:
            logger.error(f"Critical error initializing Structured Memory: {e}", exc_info=True)
            self.memory = None # Ensure memory is None if init fails

        # --- Initialize Tool Manager ---
        try:
             self.tool_manager = ToolManager()
             # Register available tools - Add more tools here as they are created
             calculator = CalculatorTool()
             self.tool_manager.register_tool(calculator)
             # Example of registering via class:
             # from modules.tools.another_tool import AnotherTool
             # self.tool_manager.register_tool_class(AnotherTool, api_key="some_key")
             logger.info("ToolManager initialized and base tools registered.")
        except Exception as e:
             logger.error(f"Critical error initializing ToolManager: {e}", exc_info=True)
             # If ToolManager is critical, maybe raise error? For now, set to None.
             self.tool_manager = None


        # Load existing agents from the state directory
        self._load_all_agents()

    def _load_all_agents(self):
        """Loads all agent states from the configured directory."""
        logger.info(f"Scanning for existing agent states in {self.agent_state_dir}...")
        loaded_count = 0
        if not os.path.isdir(self.agent_state_dir):
             logger.warning(f"Agent state directory not found: {self.agent_state_dir}. Cannot load agents.")
             return

        for filename in os.listdir(self.agent_state_dir):
            if filename.endswith(".state.json"):
                agent_id_from_filename = filename.replace(".state.json", "")
                filepath = os.path.join(self.agent_state_dir, filename)
                logger.debug(f"Attempting to load state from: {filepath}")
                try:
                    with open(filepath, "r") as f:
                        state_data = json.load(f)

                    agent_id = state_data.get("agent_id")
                    agent_type = state_data.get("agent_type")
                    config = state_data.get("config", {}) # Get config from state if saved

                    if not agent_id or not agent_type:
                        logger.warning(f"Skipping state file {filename}: Missing 'agent_id' or 'agent_type'.")
                        continue

                    # Consistency check (optional but recommended)
                    if agent_id != agent_id_from_filename:
                         logger.warning(f"Agent ID mismatch in {filename}: Filename suggests '{agent_id_from_filename}', file contains '{agent_id}'. Using ID from file content.")
                         # Decide on recovery strategy if needed

                    if agent_id in self.agents:
                         logger.warning(f"Agent {agent_id} already loaded (perhaps duplicate state file?). Skipping {filename}.")
                         continue

                    # Create the agent instance - pass self (the manager)
                    agent = AgentInstance(
                        agent_id=agent_id,
                        agent_manager=self, # Pass the manager instance
                        agent_type=agent_type,
                        config=config, # Use config loaded from state
                        initial_state=state_data # Pass the full state dict for loading
                    )

                    # AgentInstance.__init__ now handles initial state merging.
                    # The load_state method is primarily for updates after creation,
                    # but the init logic is designed to handle the initial load correctly.
                    # If explicit loading post-init is preferred:
                    # agent.load_state(state_data) # Call load_state explicitly if needed

                    self.agents[agent_id] = agent
                    loaded_count += 1
                    logger.info(f"Successfully loaded agent: ID={agent_id}, Type={agent_type}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON from state file {filename}: {e}")
                except FileNotFoundError:
                     logger.error(f"State file {filename} found during scan but could not be opened (possibly deleted?).")
                except Exception as e:
                    logger.error(f"Failed to load agent state from {filename}: {e}", exc_info=True)

        logger.info(f"Finished loading agents. Total loaded: {loaded_count}")


    def create_agent(
        self,
        agent_type: str,
        config: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentInstance]:
        """
        Creates a new agent instance, assigns it an ID, saves its initial state, and adds it to the manager.

        Args:
            agent_type (str): The type/role of the agent to create.
            config (Optional[Dict[str, Any]]): Configuration for the agent.
            agent_id (Optional[str]): A specific ID to use. If None, a UUID is generated.
            initial_state (Optional[Dict[str, Any]]): Specific initial state values.

        Returns:
            Optional[AgentInstance]: The created agent instance, or None if creation failed.
        """
        if agent_id is None:
            agent_id = f"agent_{uuid.uuid4()}"
        elif agent_id in self.agents:
             logger.error(f"Cannot create agent. ID '{agent_id}' already exists.")
             return None

        logger.info(f"Creating agent: ID={agent_id}, Type={agent_type}")

        try:
            # Ensure initial_state is a dict if None
            if initial_state is None:
                initial_state = {}

            # Create the instance - pass self (the manager)
            agent = AgentInstance(
                agent_id=agent_id,
                agent_manager=self, # Pass the manager instance
                agent_type=agent_type,
                config=config,
                initial_state=initial_state
            )

            self.agents[agent_id] = agent

            # Save the initial state immediately after creation
            if not self.save_agent_state(agent_id):
                 logger.warning(f"Failed to save initial state for agent {agent_id}. Agent created but state not persisted.")
                 # Decide if this should be a critical failure

            logger.info(f"Agent created and initial state saved: ID={agent_id}")
            return agent

        except Exception as e:
            logger.error(f"Failed to create agent instance for ID {agent_id}: {e}", exc_info=True)
            # Clean up if agent was partially added
            if agent_id in self.agents:
                del self.agents[agent_id]
            return None


    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        """Retrieves an active agent instance by its ID."""
        agent = self.agents.get(agent_id)
        if not agent:
             logger.warning(f"Attempted to get non-existent or inactive agent: {agent_id}")
        return agent

    def save_agent_state(self, agent_id: str) -> bool:
        """
        Saves the current state of a specific agent to a JSON file.

        Args:
            agent_id (str): The ID of the agent whose state needs saving.

        Returns:
            bool: True if saving was successful, False otherwise.
        """
        agent = self.get_agent(agent_id)
        if not agent:
            logger.error(f"Cannot save state: Agent {agent_id} not found.")
            return False

        state_filepath = os.path.join(self.agent_state_dir, f"{agent_id}.state.json")

        try:
            current_state = agent.get_state() # Get the comprehensive state dict
            with open(state_filepath, "w") as f:
                json.dump(current_state, f, indent=4)
            logger.info(f"Saved state for agent {agent_id} to {state_filepath}")
            return True
        except IOError as e:
            logger.error(f"Failed to write state file {state_filepath}: {e}", exc_info=True)
        except TypeError as e:
             logger.error(f"Failed to serialize agent state for {agent_id} to JSON: {e}", exc_info=True)
             # This might indicate non-serializable data in the agent's state
        except Exception as e:
             logger.error(f"An unexpected error occurred saving state for agent {agent_id}: {e}", exc_info=True)

        return False


    def save_all_agent_states(self):
        """Saves the state of all currently active agents."""
        logger.info(f"Saving state for {len(self.agents)} active agents...")
        saved_count = 0
        for agent_id in list(self.agents.keys()): # Use list copy for safe iteration if needed
            if self.save_agent_state(agent_id):
                saved_count += 1
        logger.info(f"Finished saving agents. Total saved: {saved_count}")


    # --- Pass-through methods for shared resources ---

    def log_event_to_memory(self, event_type: str, source: str, details: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        """Convenience method for agents to log events via the manager's memory."""
        if self.memory:
            try:
                self.memory.log_event(
                    event_type=event_type,
                    source=source,
                    details=details,
                    correlation_id=correlation_id
                )
            except Exception as e:
                # Log error if memory logging itself fails
                logger.error(f"AgentManager failed to log event via StructuredMemory: {e}", exc_info=True)
        else:
            logger.warning(f"Memory not available. Could not log event: Type={event_type}, Source={source}")

    def shutdown(self):
        """Performs cleanup actions like saving all agent states and closing connections."""
        logger.info("AgentManager shutting down...")
        self.save_all_agent_states()
        if self.memory:
            try:
                 self.memory.close()
            except Exception as e:
                 logger.error(f"Error closing structured memory connection during shutdown: {e}", exc_info=True)
        # Add shutdown for ToolManager if needed (e.g., closing network connections)
        logger.info("AgentManager shutdown complete.")

    def __del__(self):
        # Basic cleanup attempt if shutdown() wasn't called explicitly
        # Note: __del__ behavior can be unreliable; explicit shutdown is preferred.
        # self.shutdown() # Calling complex logic like file I/O in __del__ is risky
        if hasattr(self, 'memory') and self.memory and hasattr(self.memory, 'conn') and self.memory.conn:
             logger.warning("AgentManager deleted without explicit shutdown. Attempting memory close.")
             try:
                  self.memory.close()
             except: # Ignore errors during __del__ cleanup
                  pass

