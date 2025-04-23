import logging
import os
import json
import uuid
import inspect
from typing import Dict, Optional, Any, Type, List

# --- Core component imports ---
from modules.memory.structured_memory import StructuredMemory
# <<< ADDED: Import TaskQueue >>>
from .task_queue import TaskQueue
# --- Tool imports ---
from modules.tools.tool_manager import ToolManager
try:
    tool_manager_file_path = inspect.getfile(ToolManager)
    # Use print for initial debug before logging might be fully set up if needed
    # print(f"DEBUG: Inspecting ToolManager - found file: {tool_manager_file_path}")
except TypeError as e:
    print(f"DEBUG: Could not inspect ToolManager file path: {e}")
except Exception as e:
    print(f"DEBUG: An unexpected error occurred during ToolManager inspection: {e}")

# --- Agent instance import ---
from .agent_instance import AgentInstance


logger = logging.getLogger(__name__)

DEFAULT_AGENT_STATE_DIR = os.path.join(os.path.expanduser("~"), ".cpas3", "agents")
DEFAULT_MEMORY_DB_PATH = os.path.join(os.path.expanduser("~"), ".cpas3", "cpas_memory.db")


class AgentManager:
    """
    Manages the lifecycle, state, and interactions of multiple agent instances.
    Provides access to shared resources like memory, tools, and the task queue. # <<< Updated docstring
    """

    def __init__(
        self,
        agent_state_dir: str = DEFAULT_AGENT_STATE_DIR,
        memory_db_path: str = DEFAULT_MEMORY_DB_PATH,
        tool_config: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """
        Initializes the AgentManager.

        Args:
            agent_state_dir (str): Directory to store/load agent state files.
            memory_db_path (str): Path to the structured memory database file.
            tool_config (Optional[Dict[str, Dict[str, Any]]]): Configuration for tools,
                passed to the ToolManager during initialization. Keys are tool class names,
                values are dicts of arguments for the tool's __init__.
        """
        self.agent_state_dir = agent_state_dir
        self.memory_db_path = memory_db_path
        self.agents: Dict[str, AgentInstance] = {}
        self._tool_config = tool_config if tool_config else {} # Store config internally

        # Ensure the agent state directory exists
        try:
            os.makedirs(self.agent_state_dir, exist_ok=True)
            logger.info(f"Agent state storage initialized at: {self.agent_state_dir}")
        except OSError as e:
            logger.error(f"Failed to create agent state directory {self.agent_state_dir}: {e}", exc_info=True)
            # Decide if this is critical - maybe allow running without persistence? For now, log and continue.

        # --- Initialize Structured Memory ---
        try:
            self.memory = StructuredMemory(db_path=self.memory_db_path)
            if self.memory.conn:
                 logger.info(f"Structured Memory initialized at: {self.memory_db_path}")
            else:
                 logger.error("Failed to initialize Structured Memory. Memory operations will not work.")
                 self.memory = None
        except Exception as e:
            logger.error(f"Critical error initializing Structured Memory: {e}", exc_info=True)
            self.memory = None

        # --- Initialize Tool Manager ---
        try:
             logger.debug(f"Attempting to initialize ToolManager with config: {self._tool_config}")
             self.tool_manager = ToolManager(tool_config=self._tool_config)
             logger.debug("ToolManager instance created successfully.")

             loaded_tools = self.tool_manager.get_all_tools()
             if loaded_tools:
                  logger.info(f"ToolManager initialized. Loaded tools: {[tool.name for tool in loaded_tools]}")
             else:
                  logger.warning("ToolManager initialized, but no tools were loaded. Check tool files and configurations.")

        except Exception as e:
             logger.error(f"Critical error initializing ToolManager ({type(e).__name__}): {e}", exc_info=True)
             self.tool_manager = None # Ensure it's None if initialization fails

        # --- <<< ADDED: Initialize Task Queue >>> ---
        try:
            self.task_queue = TaskQueue()
            logger.info("TaskQueue initialized.")
        except Exception as e:
            logger.error(f"Critical error initializing TaskQueue: {e}", exc_info=True)
            self.task_queue = None # Ensure it's None if initialization fails
        # --- End Task Queue Init ---


        # Load existing agents from the state directory
        # Needs to happen *after* other components are initialized so they can be passed
        self._load_all_agents()


    # --- Keep the rest of the AgentManager methods as they were ---
    # (_load_all_agents, create_agent, get_agent, save_agent_state,
    #  save_all_agent_states, log_event_to_memory, shutdown, __del__)

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
                    config = state_data.get("config", {})

                    if not agent_id or not agent_type:
                        logger.warning(f"Skipping state file {filename}: Missing 'agent_id' or 'agent_type'.")
                        continue

                    if agent_id != agent_id_from_filename:
                         logger.warning(f"Agent ID mismatch in {filename}: Filename suggests '{agent_id_from_filename}', file contains '{agent_id}'. Using ID from file content.")

                    if agent_id in self.agents:
                         logger.warning(f"Agent {agent_id} already loaded. Skipping {filename}.")
                         continue

                    # <<< CRITICAL: Ensure all required components are available before creating AgentInstance >>>
                    if self.tool_manager is None or self.task_queue is None:
                        logger.error(f"Cannot load agent {agent_id}: ToolManager or TaskQueue failed to initialize earlier.")
                        continue # Skip loading this agent if core components are missing

                    agent = AgentInstance(
                        agent_id=agent_id,
                        agent_manager=self, # Pass self (AgentManager)
                        agent_type=agent_type,
                        config=config,
                        initial_state=state_data
                    )
                    self.agents[agent_id] = agent
                    loaded_count += 1
                    logger.info(f"Successfully loaded agent: ID={agent_id}, Type={agent_type}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON from state file {filename}: {e}")
                except FileNotFoundError:
                     logger.error(f"State file {filename} found but could not be opened.")
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
        """
        # <<< CRITICAL: Ensure required components are available before creating AgentInstance >>>
        if self.tool_manager is None or self.task_queue is None:
            logger.error(f"Cannot create agent: ToolManager or TaskQueue failed to initialize earlier.")
            return None # Cannot create agents if core components are missing

        if agent_id is None:
            agent_id = f"agent_{uuid.uuid4()}"
        elif agent_id in self.agents:
             logger.error(f"Cannot create agent. ID '{agent_id}' already exists.")
             return None

        logger.info(f"Creating agent: ID={agent_id}, Type={agent_type}")

        try:
            if initial_state is None: initial_state = {}
            agent = AgentInstance(
                agent_id=agent_id,
                agent_manager=self, # Pass self (AgentManager)
                agent_type=agent_type,
                config=config,
                initial_state=initial_state
            )
            self.agents[agent_id] = agent
            if not self.save_agent_state(agent_id):
                 logger.warning(f"Failed to save initial state for agent {agent_id}.")
            logger.info(f"Agent created and initial state saved: ID={agent_id}")
            return agent
        except Exception as e:
            logger.error(f"Failed to create agent instance for ID {agent_id}: {e}", exc_info=True)
            if agent_id in self.agents: del self.agents[agent_id] # Clean up if creation failed mid-way
            return None


    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        """Retrieves an active agent instance by its ID."""
        agent = self.agents.get(agent_id)
        if not agent: logger.warning(f"Attempted to get non-existent agent: {agent_id}")
        return agent

    def save_agent_state(self, agent_id: str) -> bool:
        """Saves the current state of a specific agent to a JSON file."""
        agent = self.get_agent(agent_id)
        if not agent:
            logger.error(f"Cannot save state: Agent {agent_id} not found.")
            return False
        state_filepath = os.path.join(self.agent_state_dir, f"{agent_id}.state.json")
        try:
            current_state = agent.get_state()
            with open(state_filepath, "w") as f: json.dump(current_state, f, indent=4)
            logger.info(f"Saved state for agent {agent_id} to {state_filepath}")
            return True
        except IOError as e: logger.error(f"Failed to write state file {state_filepath}: {e}", exc_info=True)
        except TypeError as e: logger.error(f"Failed to serialize agent state for {agent_id} to JSON: {e}", exc_info=True)
        except Exception as e: logger.error(f"Unexpected error saving state for agent {agent_id}: {e}", exc_info=True)
        return False


    def save_all_agent_states(self):
        """Saves the state of all currently active agents."""
        logger.info(f"Saving state for {len(self.agents)} active agents...")
        saved_count = 0
        # Use list(self.agents.keys()) in case saving modifies the dictionary (though it shouldn't here)
        for agent_id in list(self.agents.keys()):
            if self.save_agent_state(agent_id): saved_count += 1
        logger.info(f"Finished saving agents. Total saved: {saved_count}")


    def log_event_to_memory(self, event_type: str, source: str, details: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        """Convenience method for agents to log events via the manager's memory."""
        if self.memory:
            try:
                self.memory.log_event(event_type=event_type, source=source, details=details, correlation_id=correlation_id)
            except Exception as e: logger.error(f"AgentManager failed to log event via StructuredMemory: {e}", exc_info=True)
        else: logger.warning(f"Memory not available. Could not log event: Type={event_type}, Source={source}")

    def shutdown(self):
        """Performs cleanup actions like saving all agent states and closing connections."""
        logger.info("AgentManager shutting down...")

        # --- <<< ADDED: Shutdown agents first >>> ---
        logger.info(f"Requesting shutdown for {len(self.agents)} agents...")
        for agent_id, agent in self.agents.items():
            try:
                logger.debug(f"Calling shutdown for agent {agent_id}...")
                agent.shutdown() # Request each agent instance to stop its thread/work
            except Exception as e:
                logger.error(f"Error during shutdown for agent {agent_id}: {e}", exc_info=True)
        logger.info("Finished requesting agent shutdowns.")
        # Give threads a moment to potentially finish cleanly (optional)
        # import time
        # time.sleep(1)
        # --- End agent shutdown ---

        self.save_all_agent_states()
        if self.memory:
            try: self.memory.close()
            except Exception as e: logger.error(f"Error closing structured memory connection: {e}", exc_info=True)

        # <<< ADDED: Shutdown Task Queue (if it has a shutdown method) >>>
        if self.task_queue and hasattr(self.task_queue, 'shutdown'):
             try:
                 logger.info("Shutting down TaskQueue...")
                 self.task_queue.shutdown()
             except Exception as e:
                 logger.error(f"Error shutting down TaskQueue: {e}", exc_info=True)
        # --- End Task Queue shutdown ---

        logger.info("AgentManager shutdown complete.")

    def __del__(self):
        # Attempt cleanup if shutdown wasn't called explicitly, but prefer explicit shutdown
        if hasattr(self, 'memory') and self.memory and hasattr(self.memory, 'conn') and self.memory.conn:
             logger.warning("AgentManager deleted without explicit shutdown. Attempting memory close.")
             try: self.memory.close()
             except: pass # Ignore errors during __del__

