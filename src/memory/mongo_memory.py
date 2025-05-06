"""
MongoDB-based memory adapter for LangChain
Provides conversation memory that persists in MongoDB
"""
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Update imports to use recommended packages
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import BaseChatMessageHistory
from langchain.schema.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

# MongoDB imports
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)

class MongoDBChatMessageHistory(BaseChatMessageHistory):
    """MongoDB-backed chat message history that can be used with LangChain."""
    
    def __init__(
        self,
        connection_uri: str = "mongodb://localhost:27017/",
        db_name: str = "cpas3_memory",
        collection_name: str = "chat_messages",
        session_id: str = "default",
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize MongoDB-backed chat message history
        
        Args:
            connection_uri (str): MongoDB connection URI
            db_name (str): Database name
            collection_name (str): Collection name for storing messages
            session_id (str): Unique identifier for the chat session
            username (Optional[str]): MongoDB username
            password (Optional[str]): MongoDB password
        """
        self.connection_uri = connection_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.session_id = session_id
        self.username = username
        self.password = password
        
        # Initialize MongoDB client and collection
        self._initialize_mongodb()
    
    def _initialize_mongodb(self):
        """Initialize MongoDB client and collection"""
        try:
            # Create MongoDB client
            auth = {}
            if self.username and self.password:
                auth = {"username": self.username, "password": self.password}
            
            self.client = MongoClient(self.connection_uri, **auth)
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database and collection
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            # Create indices
            self.collection.create_index("session_id")
            self.collection.create_index([("session_id", 1), ("created_at", 1)])
            
            logger.debug(f"MongoDB chat message history initialized for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB chat message history: {e}")
            raise
    
    def add_message(self, message: BaseMessage) -> None:
        """
        Add a message to the chat message history
        
        Args:
            message (BaseMessage): The message to add
        """
        # Convert LangChain message to a document
        message_type = message.type
        content = message.content
        
        # Create document
        document = {
            "session_id": self.session_id,
            "type": message_type,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "additional_kwargs": message.additional_kwargs
        }
        
        # Insert into collection
        self.collection.insert_one(document)
        logger.debug(f"Added {message_type} message to session {self.session_id}")
    
    def clear(self) -> None:
        """Clear the message history for the session"""
        self.collection.delete_many({"session_id": self.session_id})
        logger.debug(f"Cleared message history for session {self.session_id}")
    
    @property
    def messages(self) -> List[BaseMessage]:
        """
        Returns all messages in the chat history
        
        Returns:
            List[BaseMessage]: The list of messages
        """
        # Query messages sorted by timestamp
        cursor = self.collection.find(
            {"session_id": self.session_id}
        ).sort("created_at", 1)
        
        # Convert to LangChain messages
        result = []
        for doc in cursor:
            message_type = doc["type"]
            content = doc["content"]
            additional_kwargs = doc.get("additional_kwargs", {})
            
            if message_type == "human":
                result.append(HumanMessage(content=content, additional_kwargs=additional_kwargs))
            elif message_type == "ai":
                result.append(AIMessage(content=content, additional_kwargs=additional_kwargs))
            elif message_type == "system":
                result.append(SystemMessage(content=content, additional_kwargs=additional_kwargs))
            else:
                logger.warning(f"Unknown message type {message_type} in session {self.session_id}")
        
        return result

# Import BaseChatMemory for proper inheritance
from langchain.memory.chat_memory import BaseChatMemory

class MongoChatMemory(BaseChatMemory):
    """MongoDB-based chat memory for LangChain"""
    
    # Make sure memory_key is initialized properly - directly in the class definition
    memory_key: str = "chat_history"
    
    def __init__(
        self,
        chat_memory: Optional[BaseChatMessageHistory] = None,
        memory_key: str = "chat_history",
        return_messages: bool = True,
        human_prefix: str = "Human",
        ai_prefix: str = "AI",
        connection_uri: str = "mongodb://localhost:27017/",
        db_name: str = "cpas3_memory",
        collection_name: str = "chat_messages",
        session_id: str = "default"
    ):
        """
        Initialize MongoDB chat memory
        
        Args:
            chat_memory (Optional[BaseChatMessageHistory]): Chat message history
            memory_key (str): The key to store memory under
            return_messages (bool): Whether to return messages or a string
            human_prefix (str): Prefix for human messages
            ai_prefix (str): Prefix for AI messages
            connection_uri (str): MongoDB connection URI
            db_name (str): Database name
            collection_name (str): Collection name
            session_id (str): Session identifier
        """
        # Make sure to store memory_key first
        self.memory_key = memory_key
        
        # Initialize BaseChatMemory
        super().__init__(
            chat_memory=chat_memory,
            memory_key=memory_key,
            return_messages=return_messages,
            human_prefix=human_prefix,
            ai_prefix=ai_prefix,
        )
        
        # If chat_memory is not provided, initialize MongoDB message history
        if self.chat_memory is None:
            self.chat_memory = MongoDBChatMessageHistory(
                connection_uri=connection_uri,
                db_name=db_name,
                collection_name=collection_name,
                session_id=session_id
            )
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load memory variables from chat history
        
        Args:
            inputs (Dict[str, Any]): Input values
            
        Returns:
            Dict[str, Any]: Memory variables
        """
        # Get the chat history
        chat_history = self.chat_memory.messages
        
        # If returning as messages, just return the list
        if self.return_messages:
            return {self.memory_key: chat_history}
        
        # Otherwise, serialize to string with prefixes
        buffer = []
        for message in chat_history:
            if message.type == "human":
                buffer.append(f"{self.human_prefix}: {message.content}")
            elif message.type == "ai":
                buffer.append(f"{self.ai_prefix}: {message.content}")
            elif message.type == "system":
                buffer.append(f"System: {message.content}")
        
        # Join the buffer with newlines
        result = "\n".join(buffer)
        return {self.memory_key: result}
    
    @property
    def memory_variables(self) -> List[str]:
        """
        Return the memory variables used by the memory
        
        Returns:
            List[str]: The memory variables
        """
        return [self.memory_key]

def create_mongodb_memory(
    connection_uri: str = "mongodb://localhost:27017/",
    db_name: str = "cpas3_memory",
    collection_name: str = "chat_messages",
    session_id: str = "default",
    memory_key: str = "chat_history",
    return_messages: bool = True
) -> MongoChatMemory:
    """
    Create a MongoDB-backed chat memory for LangChain
    
    Args:
        connection_uri (str): MongoDB connection URI
        db_name (str): Database name
        collection_name (str): Collection name
        session_id (str): Session identifier
        memory_key (str): Key to use for the memory
        return_messages (bool): Whether to return messages or a string
        
    Returns:
        MongoChatMemory: The memory instance
    """
    message_history = MongoDBChatMessageHistory(
        connection_uri=connection_uri,
        db_name=db_name,
        collection_name=collection_name,
        session_id=session_id
    )
    
    return MongoChatMemory(
        chat_memory=message_history,
        memory_key=memory_key,
        return_messages=return_messages
    )
