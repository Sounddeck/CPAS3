import logging
from collections import deque
from typing import Dict, List, Optional, Deque, Any, Callable # Add Callable

# Langchain message types
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage

logger = logging.getLogger(__name__)

class HistoryManager:
    """
    Manages chat history for multiple agents, including persistence callbacks.
    """
    def __init__(
        self,
        max_history_length: Optional[int] = None,
        save_callback: Optional[Callable[[str, List[Dict[str, Any]]], None]] = None # Accept callback
    ):
        """
        Initializes the HistoryManager.

        Args:
            max_history_length: Maximum number of messages to keep per agent (None for unlimited).
            save_callback: A function to call when history changes, typically for saving.
                           It should accept (agent_id: str, history_data: List[Dict[str, Any]]).
        """
        self.histories: Dict[str, Deque[Dict[str, Any]]] = {}
        self.max_history_length = max_history_length
        self._save_callback = save_callback # Store the callback
        logger.info(f"HistoryManager initialized. Max history length per agent: {'Unlimited' if max_history_length is None else max_history_length}")
        if save_callback:
             logger.info("History save callback registered.")

    def _get_history_deque(self, agent_id: str) -> Deque[Dict[str, Any]]:
        """Gets the deque for an agent, creating it if it doesn't exist."""
        if agent_id not in self.histories:
            self.histories[agent_id] = deque()
        return self.histories[agent_id]

    def add_message(self, agent_id: str, type: str, content: str) -> Optional[Dict[str, Any]]:
        """
        Adds a message to the agent's history and triggers the save callback.

        Args:
            agent_id: The ID of the agent.
            type: The type of message ('human', 'ai', 'system').
            content: The message content.

        Returns:
            The dictionary representing the added message, or None if invalid.
        """
        if type not in ["human", "ai", "system"]:
            logger.warning(f"Invalid message type '{type}' for agent {agent_id}. Ignoring.")
            return None

        history = self._get_history_deque(agent_id)
        message = {"type": type, "content": content}
        history.append(message)
        logger.debug(f"Added message to history for agent {agent_id[:8]}: Type='{type}', Content='{content[:50]}...'")

        # Trim history if max length is set
        if self.max_history_length is not None and len(history) > self.max_history_length:
            removed = history.popleft()
            logger.debug(f"Trimmed oldest message from history for agent {agent_id[:8]}: {removed['type']}")

        # Trigger the save callback if it exists
        if self._save_callback:
            try:
                # Pass agent_id and a list representation of the current history deque
                self._save_callback(agent_id, list(history))
                logger.debug(f"Save callback triggered for agent {agent_id[:8]}.")
            except Exception as e:
                logger.error(f"Error executing save callback for agent {agent_id[:8]}: {e}", exc_info=True)

        return message

    def get_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """Returns the history for an agent as a list of dictionaries."""
        return list(self._get_history_deque(agent_id))

    def get_langchain_history(self, agent_id: str) -> List[BaseMessage]:
        """
        Returns the history formatted as a list of LangChain BaseMessage objects.
        """
        history_dicts = self.get_history(agent_id)
        messages: List[BaseMessage] = []
        for msg_dict in history_dicts:
            msg_type = msg_dict.get("type")
            content = msg_dict.get("content", "")
            if msg_type == "human":
                messages.append(HumanMessage(content=content))
            elif msg_type == "ai":
                messages.append(AIMessage(content=content))
            elif msg_type == "system":
                messages.append(SystemMessage(content=content))
            else:
                logger.warning(f"Unknown message type '{msg_type}' encountered in history for agent {agent_id}. Skipping conversion.")
        return messages

    def load_history(self, agent_id: str, history_data: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Loads history for an agent from a list of dictionaries.
        If history_data is None, it attempts to load via the (indirect) AgentStore mechanism if needed,
        but typically AgentManager pre-loads via AgentStore before calling AgentInstance.from_state.
        This method primarily ensures the loaded data is stored correctly in the deque.

        Args:
            agent_id: The ID of the agent.
            history_data: A list of message dictionaries, or None.

        Returns:
             The loaded history as a list.
        """
        history = self._get_history_deque(agent_id)
        history.clear() # Clear existing deque for this agent

        if history_data:
            # Validate and append, potentially trimming if loaded data exceeds max length
            valid_messages = []
            for msg in history_data:
                 if isinstance(msg, dict) and "type" in msg and "content" in msg:
                      valid_messages.append(msg)
                 else:
                      logger.warning(f"Invalid message format found in loaded history for agent {agent_id[:8]}. Skipping: {msg}")

            # Apply max length constraint if necessary
            if self.max_history_length is not None and len(valid_messages) > self.max_history_length:
                 start_index = len(valid_messages) - self.max_history_length
                 history.extend(valid_messages[start_index:])
                 logger.debug(f"Loaded {self.max_history_length} most recent messages for agent {agent_id[:8]} due to max length constraint.")
            else:
                 history.extend(valid_messages)
                 logger.debug(f"Loaded {len(history)} messages for agent {agent_id[:8]}.")

        else:
             logger.debug(f"No initial history data provided for agent {agent_id[:8]}. Starting fresh.")

        # No need to trigger save_callback here, as we're just loading existing state
        return list(history)


    def delete_history(self, agent_id: str):
        """Removes the history for a specific agent."""
        if agent_id in self.histories:
            del self.histories[agent_id]
            logger.info(f"In-memory history cleared for agent {agent_id[:8]}.")
        else:
            logger.debug(f"No in-memory history found to delete for agent {agent_id[:8]}.")
        # Note: Actual file deletion is handled by AgentStore.remove_agent


    def clear_all_histories(self):
        """Removes history for all agents."""
        self.histories.clear()
        logger.info("Cleared in-memory history for all agents.")
        # Note: Does not delete persisted files.
