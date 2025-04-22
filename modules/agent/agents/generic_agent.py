import logging
import time
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from langchain_core.callbacks import BaseCallbackHandler # <-- Added import

from .base_agent import Agent, AgentStatus

if TYPE_CHECKING:
    from langchain_core.language_models import BaseLanguageModel
    from ..agent_manager import AgentManager
    from ..monitoring.performance_tracker import PerformanceTracker
    # Removed BaseCallbackHandler from here as it's imported directly now

logger = logging.getLogger(__name__)

class GenericAgent(Agent):
    """
    A basic, concrete implementation of the Agent class.
    Its run loop currently does nothing but wait until stopped.
    """
    type: str = "Generic" # Class attribute for type identification

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: str = "Generic Agent",
        description: Optional[str] = None,
        llm: Optional['BaseLanguageModel'] = None,
        agent_manager: Optional['AgentManager'] = None,
        performance_tracker: Optional['PerformanceTracker'] = None,
        initial_status: AgentStatus = AgentStatus.INITIALIZING,
        state: Optional[Dict[str, Any]] = None,
        callback_handlers: Optional[List[BaseCallbackHandler]] = None,
        **kwargs # Allow for extra args if needed in the future
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description or "A generic agent without specific task logic.",
            llm=llm,
            agent_manager=agent_manager,
            performance_tracker=performance_tracker,
            initial_status=initial_status,
            state=state,
            callback_handlers=callback_handlers
        )
        logger.info(f"GenericAgent '{self.name}' ({self.id}) initialized.")
        # Generic agents might not need specific tools or memory by default

    def _run(self):
        """
        Main execution logic for the GenericAgent.
        Currently, it just stays idle until stopped.
        """
        logger.info(f"GenericAgent {self.name} run loop started. Will remain idle.")
        self.set_status(AgentStatus.IDLE, "Generic agent started, waiting for tasks or stop signal.")

        while not self._stop_event.is_set():
            # Generic agent doesn't actively process tasks from a queue in this basic form.
            # It just waits to be stopped.
            # Check for stop signal periodically.
            stopped = self._stop_event.wait(timeout=1.0) # Wait for 1 second or until stop is set
            if stopped:
                logger.debug(f"GenericAgent {self.name} received stop signal.")
                break
            # Add any generic background behavior here if needed in the future.

        logger.info(f"GenericAgent {self.name} run loop finished.")
        # Status should be set to STOPPED by the stop() method or the wrapper

    def get_serializable_state(self) -> Dict[str, Any]:
        """Return the agent's current state for persistence."""
        state = super().get_serializable_state()
        # Add any GenericAgent-specific state here if needed
        # state.update({...})
        return state

    def restore_state(self, state: Dict[str, Any]):
        """Restores the agent's state from a dictionary."""
        super().restore_state(state)
        # Restore any GenericAgent-specific state here if needed
        logger.debug(f"Restored state for GenericAgent {self.name}.")

    # You might add methods here specific to generic agents later,
    # e.g., a method to accept a simple instruction via the manager.

