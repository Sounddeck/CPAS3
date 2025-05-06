"""
Simplified memory implementation for CPAS3
Provides a basic chat memory system without relying on complex inheritance
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# MongoDB imports
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

# LangChain imports for message types
from langchain.schema.messages import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

class SimpleMemory:
    """
    Simple chat memory implementation for CPAS3
    Stores messages in MongoDB without relying on LangChain's memory classes
    """
    
    def __init__(
        self,
        connection_uri: str = "mongodb://localhost:27017/",
        db_name: str = "cpas3_memory",
        collection_name: str = "simple_chat_history",
        session_id: str = "default"
    ):
        """
        Initialize simple memory
        
        Args:
            connection_uri (str): MongoDB connection URI
            db_name (str): Database name
            collection_name (str): Collection name
            session_id (str): Session identifier
        """
        self.connection_uri = connection_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.session_id = session_id
        
        # Initialize MongoDB
        self._initialize_mongodb()
    
    def _initialize_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            # Connect to MongoDB
            self.client = MongoClient(self.connection_uri)
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database and collection
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            # Create indices
            self.collection.create_index("session_id")
            self.collection.create_index([("session_id", 1), ("timestamp", 1)])
            
            logger.debug(f"SimpleMemory initialized with MongoDB at {self.connection_uri}")
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB for SimpleMemory: {e}")
            raise
    
    def add_user_message(self, content: str):
        """
        Add a user message to the chat history
        
        Args:
            content (str): Message content
        """
        self._add_message("human", content)
    
    def add_ai_message(self, content: str):
        """
        Add an AI message to the chat history
        
        Args:
            content (str): Message content
        """
        self._add_message("ai", content)
    
    def add_system_message(self, content: str):
        """
        Add a system message to the chat history
        
        Args:
            content (str): Message content
        """
        self._add_message("system", content)
    
    def _add_message(self, role: str, content: str):
        """
        Add a message to the chat history
        
        Args:
            role (str): Message role (human, ai, system)
            content (str): Message content
        """
        try:
            # Create document
            document = {
                "session_id": self.session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            # Insert into collection
            self.collection.insert_one(document)
            logger.debug(f"Added {role} message to session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error adding message to SimpleMemory: {e}")
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """
        Get the chat history for the current session
        
        Returns:
            List[Dict[str, str]]: List of message dictionaries with role and content
        """
        try:
            # Query messages sorted by timestamp
            cursor = self.collection.find(
                {"session_id": self.session_id}
            ).sort("timestamp", 1)
            
            # Convert to simple dictionaries
            result = []
            for doc in cursor:
                result.append({
                    "role": doc["role"],
                    "content": doc["content"]
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting chat history from SimpleMemory: {e}")
            return []
    
    def get_chat_history_as_string(self, human_prefix: str = "Human", ai_prefix: str = "AI") -> str:
        """
        Get the chat history as a formatted string
        
        Args:
            human_prefix (str): Prefix for human messages
            ai_prefix (str): Prefix for AI messages
            
        Returns:
            str: Formatted chat history
        """
        # Get chat history
        history = self.get_chat_history()
        
        # Format messages
        formatted_messages = []
        for message in history:
            role = message["role"]
            content = message["content"]
            
            if role == "human":
                formatted_messages.append(f"{human_prefix}: {content}")
            elif role == "ai":
                formatted_messages.append(f"{ai_prefix}: {content}")
            elif role == "system":
                formatted_messages.append(f"System: {content}")
        
        # Join with newlines
        return "\n".join(formatted_messages)
    
    def get_langchain_messages(self) -> List[Any]:
        """
        Get the chat history as LangChain message objects
        
        Returns:
            List[Any]: List of LangChain message objects
        """
        try:
            # Query messages sorted by timestamp
            cursor = self.collection.find(
                {"session_id": self.session_id}
            ).sort("timestamp", 1)
            
            # Convert to LangChain messages
            result = []
            for doc in cursor:
                role = doc["role"]
                content = doc["content"]
                
                if role == "human":
                    result.append(HumanMessage(content=content))
                elif role == "ai":
                    result.append(AIMessage(content=content))
                elif role == "system":
                    result.append(SystemMessage(content=content))
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting LangChain messages from SimpleMemory: {e}")
            return []
    
    def clear(self):
        """Clear the chat history for the current session"""
        try:
            self.collection.delete_many({"session_id": self.session_id})
            logger.debug(f"Cleared chat history for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error clearing chat history in SimpleMemory: {e}")
