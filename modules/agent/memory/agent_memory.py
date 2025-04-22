import logging
from typing import List, Dict, Any, Optional
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from langchain.memory import ConversationBufferMemory

logger = logging.getLogger(__name__)

class AgentMemory(ConversationBufferMemory):
    """
    Custom memory class for agents, potentially extending ConversationBufferMemory
    or other LangChain memory types.

    This implementation uses ConversationBufferMemory as a base, storing
    messages in memory and allowing retrieval. It adds serialization methods.
    """

    def __init__(
        self,
        agent_id: str,
        session_id: Optional[str] = None, # Optional session ID for multi-turn conversations within an agent
        chat_memory: Optional[BaseChatMessageHistory] = None,
        memory_key: str = "history", # Default key used by ConversationBufferMemory
        input_key: Optional[str] = None, # Typically 'input'
        output_key: Optional[str] = None, # Typically 'output' or 'response'
        return_messages: bool = True, # Return BaseMessage objects
        human_prefix: str = "Human",
        ai_prefix: str = "AI",
        **kwargs: Any,
    ):
        # Use agent_id as the default session_id if none provided
        self.session_id = session_id or agent_id
        self.agent_id = agent_id

        # Initialize the base ConversationBufferMemory
        # CRITICAL CHANGE: Do NOT pass session_id to the base class constructor
        super().__init__(
            chat_memory=chat_memory, # Pass along if provided
            memory_key=memory_key,
            input_key=input_key,
            output_key=output_key,
            return_messages=return_messages,
            human_prefix=human_prefix,
            ai_prefix=ai_prefix,
            **kwargs, # Pass any other relevant args for ConversationBufferMemory
        )
        logger.debug(f"AgentMemory initialized for agent {agent_id} with session_id {self.session_id}")

    def get_serializable_state(self) -> Dict[str, Any]:
        """Returns a dictionary representing the memory state for persistence."""
        try:
            # Get messages from the underlying chat history object
            messages = self.chat_memory.messages
            # Serialize messages to dictionaries
            serialized_messages = [message_to_dict(msg) for msg in messages]
            state = {
                "session_id": self.session_id,
                "agent_id": self.agent_id,
                "memory_key": self.memory_key,
                "input_key": self.input_key,
                "output_key": self.output_key,
                "return_messages": self.return_messages,
                "human_prefix": self.human_prefix,
                "ai_prefix": self.ai_prefix,
                "messages": serialized_messages,
                # Include any other relevant parameters if needed
            }
            logger.debug(f"Serialized memory state for agent {self.agent_id}, {len(serialized_messages)} messages.")
            return state
        except Exception as e:
            logger.error(f"Error serializing memory state for agent {self.agent_id}: {e}", exc_info=True)
            return {"error": f"Failed to serialize memory: {e}"}


    def load_from_state(self, state: Dict[str, Any]):
        """Loads the memory state from a dictionary."""
        try:
            self.session_id = state.get("session_id", self.agent_id) # Restore session_id
            self.agent_id = state.get("agent_id", self.agent_id) # Restore agent_id
            self.memory_key = state.get("memory_key", "history")
            self.input_key = state.get("input_key")
            self.output_key = state.get("output_key")
            self.return_messages = state.get("return_messages", True)
            self.human_prefix = state.get("human_prefix", "Human")
            self.ai_prefix = state.get("ai_prefix", "AI")

            # Deserialize messages
            serialized_messages = state.get("messages", [])
            messages = messages_from_dict(serialized_messages)

            # Clear existing messages and add loaded ones
            self.chat_memory.clear()
            for msg in messages:
                self.chat_memory.add_message(msg)

            logger.info(f"Loaded memory state for agent {self.agent_id}, {len(messages)} messages.")

        except Exception as e:
            logger.error(f"Error loading memory state for agent {self.agent_id}: {e}", exc_info=True)
            # Optionally clear memory on load failure
            self.chat_memory.clear()

    # You can add more custom methods here if needed, e.g.,
    # - Summarization logic
    # - Vector store integration
    # - Specific ways to query or manipulate memory

    def __repr__(self) -> str:
        return f"AgentMemory(agent_id='{self.agent_id}', session_id='{self.session_id}', messages={len(self.chat_memory.messages)})"

