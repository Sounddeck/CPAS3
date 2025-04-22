import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from langchain_core.callbacks import CallbackManager, BaseCallbackHandler

if TYPE_CHECKING:
    from langchain_core.language_models import BaseLanguageModel
    from ..agent_manager import AgentManager # Use relative import for AgentManager
    from ..monitoring.performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Enumeration for agent lifecycle states."""
    INITIALIZING = "Initializing"
    IDLE = "Idle"
    RUNNING = "Running"
    THINKING = "Thinking" # Specific state for processing/LLM calls
    STOPPED = "Stopped"
    FAILED = "Failed" # Task execution failed
    ERROR = "Error"   # Internal agent error (config, etc.)
    COMPLETED = "Completed" # Task finished successfully (can go back to IDLE)
    UNKNOWN = "Unknown"

class Agent(ABC):
    """
    Abstract base class for all agents in the CPAS3 system.
    Defines the common interface and lifecycle management.
    """
    type: str = "Generic" # Default agent type

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Unnamed Agent",
        description: Optional[str] = None,
        llm: Optional['BaseLanguageModel'] = None,
        agent_manager: Optional['AgentManager'] = None,
        performance_tracker: Optional['PerformanceTracker'] = None,
        initial_status: AgentStatus = AgentStatus.INITIALIZING, # <-- Added parameter
        state: Optional[Dict[str, Any]] = None,
        # Add callback_handlers parameter
        callback_handlers: Optional[List[BaseCallbackHandler]] = None,
    ):
        """
        Initializes the base agent.

        Args:
            agent_id: A unique identifier for the agent. If None, a new UUID is generated.
            name: A human-readable name for the agent.
            description: A brief description of the agent's purpose.
            llm: The language model instance the agent will use.
            agent_manager: Reference to the agent manager for coordination.
            performance_tracker: Reference to the performance tracker.
            initial_status: The starting status of the agent.
            state: A dictionary containing previously saved state to restore from.
            callback_handlers: List of LangChain callback handlers for instrumentation.
        """
        self.id = agent_id or str(uuid.uuid4())
        self.name = name
        self.description = description or "A generic agent."
        self.llm = llm
        self.agent_manager = agent_manager
        self.performance_tracker = performance_tracker
        self._status: AgentStatus = AgentStatus.UNKNOWN # Internal status
        self._status_message: str = "" # Optional message with status
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.state: Dict[str, Any] = state or {} # Holds persistent state

        # Initialize CallbackManager
        self.callback_manager = CallbackManager(callback_handlers or [])

        # Restore state if provided
        if state:
            self.restore_state(state)
            # Ensure status from state is prioritized if available
            saved_status_str = state.get('status')
            saved_status_msg = state.get('status_message', '')
            if saved_status_str:
                try:
                    saved_status = AgentStatus(saved_status_str)
                    self.set_status(saved_status, saved_status_msg)
                    logger.info(f"Agent '{self.name}' ({self.id}) restored status to {saved_status.value}")
                except ValueError:
                    logger.warning(f"Agent '{self.name}' ({self.id}) found invalid status '{saved_status_str}' in state. Setting to {initial_status.value}.")
                    self.set_status(initial_status, "Invalid status in saved state") # Use initial_status if saved one is bad
            else:
                 # If no status in state, use the provided initial_status
                 self.set_status(initial_status)
                 logger.info(f"Agent '{self.name}' ({self.id}) initialized with status {initial_status.value} (no status in saved state).")

        else:
            # If no state provided at all, set the initial status
            self.set_status(initial_status)
            logger.info(f"Agent '{self.name}' ({self.id}) initialized with status {initial_status.value}.")


        if self.llm:
             logger.info(f"Agent '{self.name}' received LLM: {self.llm.__class__.__name__}")
        if self.performance_tracker:
             self.performance_tracker.register_agent(self.id, self.name)
             logger.debug(f"Agent '{self.name}' ({self.id}) registered with PerformanceTracker.")


    @property
    def status(self) -> AgentStatus:
        """Returns the current status of the agent."""
        return self._status

    @property
    def status_message(self) -> str:
        """Returns the optional message associated with the current status."""
        return self._status_message

    def set_status(self, new_status: AgentStatus, message: str = ""):
        """Sets the agent's status and notifies relevant components."""
        if not isinstance(new_status, AgentStatus):
            logger.error(f"Invalid status type provided to agent {self.name}: {type(new_status)}. Setting to UNKNOWN.")
            new_status = AgentStatus.UNKNOWN
            message = f"Internal Error: Invalid status type {type(new_status)}"

        if self._status != new_status or self._status_message != message:
            old_status = self._status
            self._status = new_status
            self._status_message = message
            logger.debug(f"Agent {self.name} ({self.id}) status changed from {old_status.value} to {new_status.value}" + (f": {message}" if message else ""))
            # Notify AgentManager (if available) about the status change
            if self.agent_manager:
                try:
                    # Use a non-blocking call if AgentManager might be busy
                    # Or ensure AgentManager handles updates quickly
                    self.agent_manager.notify_agent_status_change(self.id, new_status, message)
                except Exception as e:
                    logger.error(f"Failed to notify AgentManager about status change for {self.name}: {e}", exc_info=True)
            # Persist state on significant status changes (optional, depends on desired frequency)
            # self.save_state()

    def start(self):
        """Starts the agent's execution in a separate thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"Agent {self.name} is already running.")
            return

        # Only start if in a startable state
        if self.status not in [AgentStatus.IDLE, AgentStatus.STOPPED, AgentStatus.FAILED, AgentStatus.COMPLETED, AgentStatus.INITIALIZING, AgentStatus.ERROR]:
             logger.warning(f"Agent {self.name} cannot start from status {self.status.value}. Current status: {self.status_message}")
             # Optionally force status to IDLE before starting? Risky.
             # self.set_status(AgentStatus.IDLE, "Resetting status to allow start.")
             return


        self._stop_event.clear()
        self.set_status(AgentStatus.RUNNING)
        self._thread = threading.Thread(target=self._run_wrapper, daemon=True)
        self._thread.start()
        logger.info(f"Agent {self.name} started.")

    def stop(self):
        """Signals the agent to stop its execution."""
        if self._thread is None or not self._thread.is_alive():
            logger.warning(f"Agent {self.name} is not running.")
            # Ensure status reflects stopped state even if thread wasn't running
            if self.status != AgentStatus.STOPPED:
                 self.set_status(AgentStatus.STOPPED, "Agent was not running.")
            return

        if self.status == AgentStatus.STOPPED:
             logger.info(f"Agent {self.name} is already stopping or stopped.")
             return

        logger.info(f"Stopping agent {self.name}...")
        self.set_status(AgentStatus.STOPPED, "Stop requested.")
        self._stop_event.set()
        # Wait for the thread to finish (optional, with timeout)
        # self._thread.join(timeout=5.0)
        # if self._thread.is_alive():
        #     logger.warning(f"Agent {self.name} thread did not stop within timeout.")
        # else:
        #     logger.info(f"Agent {self.name} stopped successfully.")
        # self._thread = None # Clear thread reference
        # self.save_state() # Persist state after stopping

    def _run_wrapper(self):
        """Internal wrapper to handle execution and status updates."""
        try:
            self._run()
            # If _run finishes without error and wasn't stopped, set to IDLE or COMPLETED
            if not self._stop_event.is_set() and self.status == AgentStatus.RUNNING:
                 # Default to IDLE, specific agents might set COMPLETED in _run
                 self.set_status(AgentStatus.IDLE, "Run loop finished normally.")
        except Exception as e:
            logger.error(f"Unhandled exception in agent {self.name} run loop: {e}", exc_info=True)
            self.set_status(AgentStatus.ERROR, f"Runtime error: {e}")
        finally:
            # Ensure status is not RUNNING if the loop exits
            if self.status == AgentStatus.RUNNING:
                 # If stop was requested, status should already be STOPPED
                 if self._stop_event.is_set():
                      # Already handled by stop() or within _run()
                      pass
                 else:
                      # Exited unexpectedly without stop signal
                      logger.warning(f"Agent {self.name} run loop exited unexpectedly while status was RUNNING. Setting to ERROR.")
                      self.set_status(AgentStatus.ERROR, "Run loop exited unexpectedly.")
            logger.info(f"Agent {self.name} thread finished.")
            self._thread = None # Clear thread reference after it finishes


    @abstractmethod
    def _run(self):
        """
        The main execution logic of the agent.
        This method should periodically check `self._stop_event.is_set()`
        and exit gracefully if it's true.
        Subclasses MUST implement this method.
        """
        pass

    def get_serializable_state(self) -> Dict[str, Any]:
        """
        Returns a dictionary representing the agent's current state,
        suitable for persistence (e.g., JSON serialization).
        Subclasses should override and extend this to include specific state.
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type, # Include agent type
            "description": self.description,
            "status": self.status.value,
            "status_message": self.status_message,
            # LLM and AgentManager are dependencies, not typically serialized directly.
            # PerformanceTracker is also usually external.
            # Custom state from self.state can be added here or by subclasses
            **self.state # Include any custom state stored
        }

    def save_state(self):
        """Requests the AgentManager to persist the agent's current state."""
        if self.agent_manager:
            try:
                current_state = self.get_serializable_state()
                self.agent_manager.save_agent_state(self.id, current_state)
                logger.debug(f"Requested state save for agent {self.name} ({self.id})")
            except Exception as e:
                logger.error(f"Failed to request state save for agent {self.name}: {e}", exc_info=True)
        else:
            logger.warning(f"Cannot save state for agent {self.name}: AgentManager not available.")

    def restore_state(self, state: Dict[str, Any]):
        """
        Restores the agent's state from a dictionary.
        Subclasses can override this to handle specific state restoration.
        """
        self.id = state.get('id', self.id) # Should generally match
        self.name = state.get('name', self.name)
        self.description = state.get('description', self.description)
        # Status is handled in __init__ based on state
        # self.status = AgentStatus(state.get('status', AgentStatus.UNKNOWN.value))
        # self.status_message = state.get('status_message', '')

        # Restore custom state items, excluding core attributes handled above
        core_attrs = {'id', 'name', 'description', 'status', 'status_message', 'type'}
        custom_state = {k: v for k, v in state.items() if k not in core_attrs}
        self.state.update(custom_state)

        logger.debug(f"Restored basic state for agent {self.name} from provided dictionary.")

    def add_callback_handler(self, handler: BaseCallbackHandler):
        """Adds a callback handler to the agent's CallbackManager."""
        self.callback_manager.add_handler(handler, inherit=True)
        logger.info(f"Added callback handler {handler.__class__.__name__} to agent {self.name}")

    def remove_callback_handler(self, handler: BaseCallbackHandler):
        """Removes a callback handler from the agent's CallbackManager."""
        self.callback_manager.remove_handler(handler)
        logger.info(f"Removed callback handler {handler.__class__.__name__} from agent {self.name}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.id}', name='{self.name}', status='{self.status.value}')"
