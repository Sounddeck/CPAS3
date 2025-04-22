import logging
import time
from typing import Dict, Any, Optional, List

# --- Remove AgentType import ---
from .base_agent import Agent, AgentStatus
# --- End Removal ---

# --- Keep these imports ---
from langchain_core.language_models import BaseLanguageModel
from langchain_core.tools import BaseTool
# --- End Keep ---

# Forward declaration for type hinting AgentManager
if False:
    from ..agent_manager import AgentManager

logger = logging.getLogger(__name__)

class SearchAgent(Agent):
    """
    An agent specifically designed for search-related tasks.
    Inherits from the base Agent class.
    (Note: Functionality is largely placeholder for now)
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        agent_manager: 'AgentManager',
        llm: Optional[BaseLanguageModel],
        tools: Optional[List[BaseTool]],
        performance_tracker,
        config: Optional[Dict[str, Any]] = None,
        status: AgentStatus = AgentStatus.INITIALIZING
    ):
        """
        Initializes a SearchAgent instance.
        Calls the base class initializer.
        """
        # --- No longer pass AgentType ---
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            agent_manager=agent_manager,
            llm=llm,
            tools=tools,
            performance_tracker=performance_tracker,
            config=config or {},
            status=status
        )
        # --- End Change ---
        self.type = "Search" # Explicitly set type
        logger.info(f"SearchAgent '{self.name}' ({self.id}) initialized.")

    def _process_task(self, task_data: Dict):
        """
        Overrides the base class method for search-specific task processing.
        Placeholder implementation.
        """
        start_time = time.time()
        task_id = task_data.get("task_id", "unknown")
        logger.info(f"SearchAgent {self.name} processing task {task_id}: {task_data}")

        # --- Search Task Processing Logic ---
        query = task_data.get("query")

        if self.llm and query:
            # Placeholder: Maybe use LLM to refine query or decide which search tool to use
            logger.info(f"SearchAgent {self.name} received query: {query}")
            # Example: Find a specific 'web_search' tool if available
            search_tool = self.agent_manager.get_tool("web_search_tool") # Hypothetical tool name
            if search_tool:
                 try:
                      logger.info(f"SearchAgent attempting to use {search_tool.name}...")
                      search_result = search_tool.invoke({"query": query})
                      logger.info(f"Search tool result: {search_result[:200]}...")
                      # Feed result back to LLM or format for user
                 except Exception as e:
                      logger.error(f"Error invoking search tool: {e}")
            else:
                 logger.warning("No 'web_search_tool' available for SearchAgent.")
                 # Fallback or error handling

            duration = time.time() - start_time
            self.performance_tracker.log_task(self.id, task_id, duration, True) # Assume success
            logger.info(f"SearchAgent {self.name} finished processing task {task_id} in {duration:.2f} seconds.")

        else:
            logger.warning(f"SearchAgent {self.name} cannot process task {task_id}: LLM not available or no 'query' in task data.")
            time.sleep(1)
            duration = time.time() - start_time
            self.performance_tracker.log_task(self.id, task_id, duration, False) # Log failure
        # --- End Search Task Processing Logic ---


    # Inherits run(), stop(), get_status(), update_config(), etc. from BaseAgent
    # Inherits get_serializable_state() and from_serializable_state()

    @classmethod
    def from_serializable_state(
        cls,
        state: Dict[str, Any],
        agent_manager: 'AgentManager',
        llm: Optional[BaseLanguageModel],
        tools: Optional[List[BaseTool]],
        performance_tracker
    ) -> 'SearchAgent':
        """
        Creates a SearchAgent instance from a previously serialized state dictionary.
        Relies on the base class implementation after checking type.
        """
        if state.get("type") != "Search":
             raise ValueError(f"Cannot reconstruct SearchAgent from state with type {state.get('type')}")

        agent = super(SearchAgent, cls).from_serializable_state(
             state=state,
             agent_manager=agent_manager,
             llm=llm,
             tools=tools,
             performance_tracker=performance_tracker
        )
        if not isinstance(agent, SearchAgent):
             raise TypeError(f"Reconstruction failed: Expected SearchAgent, got {type(agent)}")

        logger.info(f"SearchAgent '{agent.name}' ({agent.id}) reconstructed from state.")
        return agent

