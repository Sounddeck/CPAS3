import logging
from typing import List, Dict, Optional, Type, Any
from uuid import uuid4

# Langchain callback imports
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.callbacks.manager import CallbackManagerForLLMRun, CallbackManagerForToolRun
from langchain_core.outputs import LLMResult, AgentAction, AgentFinish
from langchain_core.messages import BaseMessage

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
    # logging.info("CallbackManager running without UI signal emitter.") # Less verbose


logger = logging.getLogger(__name__)

# --- Example Custom Callback Handler (for logging/UI signals) ---
# You can create more specific handlers for different purposes

class AgentCallbackHandler(BaseCallbackHandler):
    """A custom callback handler to log events and emit UI signals."""

    def __init__(self, agent_id: str, task_id: Optional[str] = None, run_id: Optional[str] = None):
        super().__init__()
        self.agent_id = agent_id
        self.task_id = task_id
        # Langchain uses run_id internally, but we might generate our own if needed
        self.run_id = run_id or str(uuid4())
        logger.debug(f"AgentCallbackHandler created for agent {agent_id[:8]}, task {task_id[:8] if task_id else 'N/A'}, run {self.run_id[:8]}")

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], *, run_id: uuid4, parent_run_id: Optional[uuid4] = None, tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Any:
        """Run when LLM starts running."""
        log_msg = f"Agent {self.agent_id[:8]} (Task: {self.task_id[:8] if self.task_id else 'N/A'}) - LLM Start (Run: {run_id.hex[:8]})"
        # logger.info(log_msg) # Can be verbose
        logger.debug(f"{log_msg} - Prompts: {prompts}") # Log prompts only at debug level
        try:
            signal_emitter.agent_llm_start.emit(self.agent_id, self.task_id, run_id.hex, prompts)
        except Exception as e:
            logger.error(f"Error emitting agent_llm_start signal: {e}", exc_info=False)


    def on_chat_model_start(
        self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], *, run_id: uuid4, parent_run_id: Optional[uuid4] = None, tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Any:
        """Run when Chat Model starts running."""
        log_msg = f"Agent {self.agent_id[:8]} (Task: {self.task_id[:8] if self.task_id else 'N/A'}) - ChatModel Start (Run: {run_id.hex[:8]})"
        # logger.info(log_msg) # Can be verbose
        # Avoid logging full message objects unless necessary, can be large
        logger.debug(f"{log_msg} - Input Messages Count: {len(messages[0]) if messages else 0}")
        try:
            # Convert messages for emission if needed, or just send IDs/types
            signal_emitter.agent_chat_model_start.emit(self.agent_id, self.task_id, run_id.hex)
        except Exception as e:
            logger.error(f"Error emitting agent_chat_model_start signal: {e}", exc_info=False)


    def on_llm_new_token(self, token: str, *, chunk: Optional[Any] = None, run_id: uuid4, parent_run_id: Optional[uuid4] = None, **kwargs: Any) -> Any:
        """Run on new LLM token. Only available when streaming is enabled."""
        # logger.debug(f"Agent {self.agent_id[:8]} - LLM Token: {token}") # Very verbose
        try:
            signal_emitter.agent_llm_token.emit(self.agent_id, self.task_id, run_id.hex, token)
        except Exception as e:
            logger.error(f"Error emitting agent_llm_token signal: {e}", exc_info=False)

    def on_llm_end(self, response: LLMResult, *, run_id: uuid4, parent_run_id: Optional[uuid4] = None, **kwargs: Any) -> Any:
        """Run when LLM ends running."""
        log_msg = f"Agent {self.agent_id[:8]} (Task: {self.task_id[:8] if self.task_id else 'N/A'}) - LLM End (Run: {run_id.hex[:8]})"
        # logger.info(log_msg) # Can be verbose
        # Avoid logging full response object unless debugging
        logger.debug(f"{log_msg} - Response Generations: {len(response.generations)}")
        try:
            # Extract relevant info from response for signal emission
            # Example: Get the first generation's text
            result_text = response.generations[0][0].text if response.generations and response.generations[0] else None
            signal_emitter.agent_llm_end.emit(self.agent_id, self.task_id, run_id.hex, result_text)
        except Exception as e:
            logger.error(f"Error emitting agent_llm_end signal: {e}", exc_info=False)

    def on_llm_error(self, error: BaseException, *, run_id: uuid4, parent_run_id: Optional[uuid4] = None, **kwargs: Any) -> Any:
        """Run when LLM errors."""
        logger.error(f"Agent {self.agent_id[:8]} (Task: {self.task_id[:8] if self.task_id else 'N/A'}) - LLM Error (Run: {run_id.hex[:8]}): {error}", exc_info=True)
        try:
            signal_emitter.agent_llm_error.emit(self.agent_id, self.task_id, run_id.hex, str(error))
        except Exception as e:
            logger.error(f"Error emitting agent_llm_error signal: {e}", exc_info=False)


    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, *, run_id: uuid4, parent_run_id: Optional[uuid4] = None, tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Any:
        """Run when tool starts running."""
        tool_name = serialized.get('name', 'Unknown Tool')
        logger.info(f"Agent {self.agent_id[:8]} (Task: {self.task_id[:8] if self.task_id else 'N/A'}) - Tool Start: '{tool_name}' (Run: {run_id.hex[:8]})")
        logger.debug(f"Tool '{tool_name}' Input: '{input_str}'")
        try:
            signal_emitter.agent_tool_start.emit(self.agent_id, self.task_id, run_id.hex, tool_name, input_str)
        except Exception as e:
            logger.error(f"Error emitting agent_tool_start signal: {e}", exc_info=False)


    def on_tool_end(
        self, output: str, *, run_id: uuid4, parent_run_id: Optional[uuid4] = None, tags: Optional[List[str]] = None, **kwargs: Any # Output type might vary based on tool
    ) -> Any:
        """Run when tool ends running."""
        # Need tool name - Langchain doesn't pass it directly here. Might need state tracking if critical.
        logger.info(f"Agent {self.agent_id[:8]} (Task: {self.task_id[:8] if self.task_id else 'N/A'}) - Tool End (Run: {run_id.hex[:8]})")
        logger.debug(f"Tool Output: '{str(output)[:100]}...'") # Log truncated output
        try:
             # Tool name isn't directly available, pass output only or enhance handler state
            signal_emitter.agent_tool_end.emit(self.agent_id, self.task_id, run_id.hex, str(output))
        except Exception as e:
            logger.error(f"Error emitting agent_tool_end signal: {e}", exc_info=False)


    def on_tool_error(self, error: BaseException, *, run_id: uuid4, parent_run_id: Optional[uuid4] = None, **kwargs: Any) -> Any:
        """Run when tool errors."""
        logger.error(f"Agent {self.agent_id[:8]} (Task: {self.task_id[:8] if self.task_id else 'N/A'}) - Tool Error (Run: {run_id.hex[:8]}): {error}", exc_info=True)
        try:
             # Tool name isn't directly available
            signal_emitter.agent_tool_error.emit(self.agent_id, self.task_id, run_id.hex, str(error))
        except Exception as e:
            logger.error(f"Error emitting agent_tool_error signal: {e}", exc_info=False)


    def on_agent_action(
        self, action: AgentAction, *, run_id: uuid4, parent_run_id: Optional[uuid4] = None, tags: Optional[List[str]] = None, **kwargs: Any
    ) -> Any:
        """Run on agent action."""
        logger.info(f"Agent {self.agent_id[:8]} (Task: {self.task_id[:8] if self.task_id else 'N/A'}) - Action: Tool='{action.tool}', Input='{action.tool_input}' (Run: {run_id.hex[:8]})")
        # Log the thought process leading to the action if available
        if action.log:
             logger.debug(f"Action Log/Thought:\n{action.log}")
        try:
            signal_emitter.agent_action.emit(self.agent_id, self.task_id, run_id.hex, action.tool, str(action.tool_input), action.log)
        except Exception as e:
            logger.error(f"Error emitting agent_action signal: {e}", exc_info=False)


    def on_agent_finish(
        self, finish: AgentFinish, *, run_id: uuid4, parent_run_id: Optional[uuid4] = None, tags: Optional[List[str]] = None, **kwargs: Any
    ) -> Any:
        """Run on agent end."""
        logger.info(f"Agent {self.agent_id[:8]} (Task: {self.task_id[:8] if self.task_id else 'N/A'}) - Agent Finish (Run: {run_id.hex[:8]})")
        # Log the final output/return values
        logger.debug(f"Final Output/Return Values: {finish.return_values}")
        try:
            signal_emitter.agent_finish.emit(self.agent_id, self.task_id, run_id.hex, finish.return_values)
        except Exception as e:
            logger.error(f"Error emitting agent_finish signal: {e}", exc_info=False)

    # Override other methods like on_text, on_chain_start/end/error if needed


# --- Callback Manager ---

class CallbackManager:
    """
    Manages various callback handlers and provides them to agents.
    Allows registering global handlers and potentially agent-specific ones.
    """
    def __init__(self):
        # Global handlers are applied to all runs unless overridden
        self.global_handlers: List[BaseCallbackHandler] = []
        # You could add logic for agent-specific handlers if required
        # self.agent_handlers: Dict[str, List[BaseCallbackHandler]] = {}
        logger.info("CallbackManager initialized.")
        self._add_default_handlers()

    def _add_default_handlers(self):
        """Adds default handlers (like logging/UI) on initialization."""
        # Note: The default AgentCallbackHandler needs agent_id/task_id.
        # We can't add a single instance globally here. Instead, we'll
        # instantiate it dynamically when get_callbacks_for_agent is called.
        logger.info("Default AgentCallbackHandler will be created dynamically per agent run.")
        # If you had other truly global handlers (not agent/task specific), add them here:
        # self.global_handlers.append(MyGlobalHandler())

    def add_global_handler(self, handler: BaseCallbackHandler):
        """Registers a callback handler to be used globally."""
        if not isinstance(handler, BaseCallbackHandler):
            raise TypeError("Handler must be an instance of BaseCallbackHandler.")
        if handler not in self.global_handlers:
            self.global_handlers.append(handler)
            logger.info(f"Global callback handler '{type(handler).__name__}' added.")

    def remove_global_handler(self, handler_type: Type[BaseCallbackHandler]):
        """Removes all instances of a specific handler type from global handlers."""
        initial_len = len(self.global_handlers)
        self.global_handlers = [h for h in self.global_handlers if not isinstance(h, handler_type)]
        removed_count = initial_len - len(self.global_handlers)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} global handler(s) of type '{handler_type.__name__}'.")

    def get_callbacks_for_agent(self, agent_id: str, task_id: Optional[str] = None, run_id: Optional[str] = None) -> List[BaseCallbackHandler]:
        """
        Gets the list of applicable callback handlers for a specific agent run.
        Includes global handlers and dynamically creates agent/task-specific ones.
        """
        callbacks: List[BaseCallbackHandler] = []

        # Add global handlers first
        callbacks.extend(self.global_handlers)

        # Add dynamically created instance of the default agent/task handler
        try:
            agent_handler = AgentCallbackHandler(agent_id=agent_id, task_id=task_id, run_id=run_id)
            callbacks.append(agent_handler)
        except Exception as e:
            logger.error(f"Failed to create AgentCallbackHandler for agent {agent_id[:8]}: {e}", exc_info=True)

        # Add any other agent-specific handlers here if logic was implemented

        logger.debug(f"Providing {len(callbacks)} callbacks for agent {agent_id[:8]}, task {task_id[:8] if task_id else 'N/A'}.")
        return callbacks

