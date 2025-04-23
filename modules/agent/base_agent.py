import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, Callable, TYPE_CHECKING
import datetime

# Import signal emitter safely
try:
    from ..ui.signal_emitter import signal_emitter
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False
    class DummySignalEmitter:
        def __getattr__(self, name):
            class DummySignal:
                def emit(self, *args, **kwargs): pass
            return DummySignal()
    signal_emitter = DummySignalEmitter()
    # logging.info("BaseAgent running without UI signal emitter.") # Less verbose

# Forward references for type hinting
if TYPE_CHECKING:
    from .agent_manager import AgentManager
    from .persistence.agent_store import AgentStore
    from .monitoring.performance_tracker import PerformanceTracker
    from .callback_manager import CallbackManager

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Represents the possible states of an agent."""
    UNKNOWN = "UNKNOWN"
    INITIALIZING = "INITIALIZING"
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    THINKING = "THINKING" # Specific state for active processing within RUNNING
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED" # Agent encountered an error during runtime
    ERROR = "ERROR"   # Agent failed to initialize or has a configuration error

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    Manages the agent's lifecycle, state, and execution thread.
    """
    type: str = "Base" # Subclasses should override this

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: Optional[str] = None,
        llm: Optional[Any] = None, # Base class doesn't mandate LLM, but subclasses might
        agent_manager: Optional['AgentManager'] = None,
        performance_tracker: Optional['PerformanceTracker'] = None,
        callback_manager: Optional['CallbackManager'] = None,
        initial_status: AgentStatus = AgentStatus.INITIALIZING,
        state: Optional[Dict[str, Any]] = None,
        on_stop_callback: Optional[Callable[[str], None]] = None,
        **kwargs # Allow for additional state parameters from subclasses or future versions
    ):
        self.id = agent_id or uuid.uuid4().hex
        self.name = name
        self.description = description
        self.llm = llm # Store LLM if provided
        self._agent_manager = agent_manager # Use weakref if cyclical deps become an issue
        self._performance_tracker = performance_tracker
        self._callback_manager = callback_manager or (agent_manager.callback_manager if agent_manager else None)
        self._status = AgentStatus.UNKNOWN # Initialize status
        self._current_task_id: Optional[str] = None
        self._created_at = datetime.datetime.now(datetime.timezone.utc)
        self._last_updated_at = self._created_at

        # Threading control
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._on_stop_callback = on_stop_callback # Manager's callback

        # Restore state if provided (should happen after basic init)
        if state:
            self._created_at = state.get('created_at', self._created_at)
            # Ensure status from state is valid, otherwise use initial_status or default
            status_from_state = state.get('status')
            try:
                if isinstance(status_from_state, AgentStatus):
                     initial_status = status_from_state
                elif isinstance(status_from_state, str):
                     initial_status = AgentStatus(status_from_state)
                # else: use the initial_status passed to __init__
            except ValueError:
                 logger.warning(f"Invalid status '{status_from_state}' in loaded state for agent {self.id}. Using {initial_status.name}.")
            # Don't restore RUNNING/STARTING states directly, set to IDLE/STOPPED instead
            if initial_status in [AgentStatus.RUNNING, AgentStatus.STARTING, AgentStatus.THINKING, AgentStatus.STOPPING]:
                 logger.info(f"Agent {self.id} loaded with active status {initial_status.name}. Setting to IDLE.")
                 initial_status = AgentStatus.IDLE # Or STOPPED, depending on desired resume behavior

        # Set initial status *after* potential state restoration
        self.set_status(initial_status, initial_setup=True)

        logger.info(f"BaseAgent '{self.name}' (ID: {self.id[:8]}) initialized.")

    @property
    def status(self) -> AgentStatus:
        """Returns the current status of the agent."""
        return self._status

    def set_status(self, new_status: AgentStatus, message: Optional[str] = None, initial_setup: bool = False):
        """
        Updates the agent's status, logs the change, emits a signal, and saves state.
        """
        if not isinstance(new_status, AgentStatus):
            logger.error(f"Invalid status type provided to set_status for agent {self.id}: {type(new_status)}. Status unchanged.")
            return

        if self._status != new_status:
            old_status = self._status
            self._status = new_status
            self._last_updated_at = datetime.datetime.now(datetime.timezone.utc)
            log_message = f"Agent '{self.name}' (ID: {self.id[:8]}) status changed from {old_status.name} to {new_status.name}"
            if message:
                log_message += f": {message}"
            logger.info(log_message)

            # Emit signal for UI update
            try:
                signal_emitter.agent_status_updated.emit(self.id, new_status) # Pass enum member
            except Exception as sig_e:
                logger.error(f"Error emitting agent_status_updated signal for {self.id[:8]}: {sig_e}", exc_info=False)

            # Add history entry? (Consider if this is too noisy)
            # self._add_history("status_change", {"old": old_status.name, "new": new_status.name, "message": message})

            # Persist state change, unless it's the very first status set during init
            if not initial_setup:
                 self.save_state()


    def get_serializable_state(self) -> Dict[str, Any]:
        """
        Returns the agent's current state as a dictionary suitable for persistence (e.g., JSON).
        Subclasses should override and call super().get_serializable_state() then update the dict.
        """
        return {
            "agent_id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "status": self.status.name, # Store enum name as string
            "created_at": self._created_at.isoformat(),
            "last_updated_at": self._last_updated_at.isoformat(),
            # LLM and Tools are dependencies, not state - re-injected by Manager on load
            # Threading objects are runtime, not state
        }

    def save_state(self):
        """Saves the agent's current state using the AgentManager's AgentStore."""
        if self._agent_manager and self._agent_manager.agent_store:
            try:
                state_data = self.get_serializable_state()
                self._agent_manager.agent_store.save_agent_state(self.id, state_data)
                # logger.debug(f"Saved state for agent {self.id[:8]}") # Can be noisy
            except Exception as e:
                logger.error(f"Failed to save state for agent '{self.name}' ({self.id[:8]}): {e}", exc_info=True)
        else:
            logger.warning(f"Cannot save state for agent '{self.name}' ({self.id[:8]}): AgentManager or AgentStore not available.")

    def start(self):
        """Starts the agent's execution thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"Agent '{self.name}' ({self.id[:8]}) is already running.")
            return
        if self.status in [AgentStatus.RUNNING, AgentStatus.STARTING, AgentStatus.THINKING]:
             logger.warning(f"Agent '{self.name}' ({self.id[:8]}) is already {self.status.name}.")
             return
        if self.status == AgentStatus.ERROR:
             logger.error(f"Cannot start agent '{self.name}' ({self.id[:8]}) because it is in ERROR state.")
             return

        logger.info(f"Starting agent '{self.name}' (ID: {self.id[:8]})...")
        self.set_status(AgentStatus.STARTING)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_wrapper, name=f"Agent-{self.name}-{self.id[:8]}")
        self._thread.daemon = True # Allow program to exit even if agent threads are running
        self._thread.start()
        logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) thread started.")
        # Status will be set to RUNNING or IDLE by the _run_wrapper

    def stop(self, wait: bool = False, timeout: float = 10.0):
        """Signals the agent's execution loop to stop."""
        if self._stop_event.is_set():
            logger.info(f"Agent '{self.name}' ({self.id[:8]}) stop already requested.")
            if self.status not in [AgentStatus.STOPPING, AgentStatus.STOPPED]:
                 self.set_status(AgentStatus.STOPPING) # Ensure status reflects intent
            return

        if not self._thread or not self._thread.is_alive():
            logger.info(f"Agent '{self.name}' ({self.id[:8]}) is not running.")
            if self.status != AgentStatus.ERROR:
                 self.set_status(AgentStatus.STOPPED)
            return

        logger.info(f"Stopping agent '{self.name}' (ID: {self.id[:8]})...")
        self.set_status(AgentStatus.STOPPING)
        self._stop_event.set() # Signal the loop to exit

        if wait and self._thread:
            logger.info(f"Waiting up to {timeout}s for agent '{self.name}' ({self.id[:8]}) thread to stop...")
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning(f"Agent '{self.name}' ({self.id[:8]}) thread did not stop within timeout.")
                # Forceful termination is generally discouraged for threads
            else:
                logger.info(f"Agent '{self.name}' ({self.id[:8]}) thread stopped.")
                if self.status != AgentStatus.ERROR: # Don't overwrite error state
                     self.set_status(AgentStatus.STOPPED)
                self._thread = None # Clear thread reference

    def _run_wrapper(self):
        """Wraps the main execution loop (_run) with setup, error handling, and cleanup."""
        # Check if already stopped before starting the loop
        if self._stop_event.is_set():
             logger.info(f"Agent '{self.name}' ({self.id[:8]}) stop requested before run loop started.")
             self.set_status(AgentStatus.STOPPED)
             if self._on_stop_callback:
                 self._on_stop_callback(self.id)
             return

        # Set initial running state (usually IDLE until a task is picked up)
        self.set_status(AgentStatus.IDLE)
        try:
            logger.info(f"Agent '{self.name}' ({self.id[:8]}) run loop starting.")
            # --- Call the subclass's main loop ---
            self._run()
            # --- Main loop finished ---

            # Determine final status based on whether stop was requested or loop exited naturally
            if self._stop_event.is_set():
                logger.info(f"Agent '{self.name}' ({self.id[:8]}) run loop finished due to stop request.")
                final_status = AgentStatus.STOPPED
            else:
                logger.warning(f"Agent '{self.name}' ({self.id[:8]}) run loop exited unexpectedly (without stop request).")
                # If the loop finishes without error but wasn't stopped, it might be IDLE or need review
                final_status = AgentStatus.IDLE # Or potentially FAILED if unexpected exit implies error

        except Exception as e:
            logger.error(f"Agent '{self.name}' ({self.id[:8]}) encountered an error in run loop: {e}", exc_info=True)
            final_status = AgentStatus.FAILED
            self.set_status(AgentStatus.FAILED, message=str(e)) # Set FAILED first
            # Optionally add error details to history here
        finally:
            logger.info(f"Agent '{self.name}' ({self.id[:8]}) run loop ended.")
            # Ensure final status is set correctly, avoid overwriting FAILED with STOPPED if error occurred before stop
            if self.status != AgentStatus.FAILED:
                 self.set_status(final_status)

            # Notify the manager that the thread has stopped
            if self._on_stop_callback:
                try:
                    self._on_stop_callback(self.id)
                except Exception as cb_e:
                     logger.error(f"Error in on_stop_callback for agent {self.id[:8]}: {cb_e}", exc_info=True)


    @abstractmethod
    def _run(self):
        """
        The main execution loop for the agent. Subclasses MUST implement this method.
        This loop should periodically check `self._stop_event.is_set()` and exit cleanly if True.
        """
        pass

    def get_callback_manager(self) -> Optional['CallbackManager']:
         """Returns the callback manager associated with the agent."""
         return self._callback_manager

    # Optional: Add helper for history logging if needed frequently by subclasses
    # def _add_history(self, entry_type: str, content: Any, task_id: Optional[str] = None):
    #     if self._agent_manager and self._agent_manager.history_manager:
    #         try:
    #             entry = HistoryEntry(entry_type=entry_type, content=content, task_id=task_id or self._current_task_id)
    #             self._agent_manager.history_manager.add(self.id, entry)
    #         except Exception as e:
    #             logger.error(f"Failed to add history entry type '{entry_type}' for agent {self.id[:8]}: {e}", exc_info=False)

