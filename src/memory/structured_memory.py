"""
StructuredMemory: MongoDB-based memory system for CPAS3
Stores user actions, system events, and agent traces for system learning and improvement
"""
import os
import json
import logging
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# MongoDB imports
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class StructuredMemory:
    """
    MongoDB-based memory system for storing structured data about interactions
    and system events.
    
    Thread-safe implementation that manages connections per-thread.
    """
    
    def __init__(
        self, 
        connection_uri: Optional[str] = None,
        db_name: str = "cpas3_memory",
        connection_timeout_ms: int = 5000
    ):
        """
        Initialize the structured memory system
        
        Args:
            connection_uri (Optional[str]): MongoDB connection URI
                If None, defaults to "mongodb://localhost:27017/"
            db_name (str): Name of the database to use
            connection_timeout_ms (int): Connection timeout in milliseconds
        """
        self.connection_uri = connection_uri or "mongodb://localhost:27017/"
        self.db_name = db_name
        self.connection_timeout_ms = connection_timeout_ms
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Test connection and initialize
        self._init_mongo()
        
        logger.info(f"StructuredMemory initialized with MongoDB at {self.connection_uri}")
    
    def _get_client(self) -> MongoClient:
        """Get a thread-local MongoDB client"""
        if not hasattr(self._local, 'client'):
            try:
                self._local.client = MongoClient(
                    self.connection_uri,
                    serverSelectionTimeoutMS=self.connection_timeout_ms
                )
                # Test connection
                self._local.client.admin.command('ping')
                logger.debug("MongoDB connection established")
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(f"Could not connect to MongoDB: {e}")
                raise
                
        return self._local.client
    
    def _get_db(self) -> Database:
        """Get the database"""
        client = self._get_client()
        return client[self.db_name]
    
    def _get_collection(self, collection_name: str) -> Collection:
        """Get a collection by name"""
        db = self._get_db()
        return db[collection_name]
    
    def _init_mongo(self):
        """Initialize MongoDB connection and create indices"""
        try:
            client = self._get_client()
            db = self._get_db()
            
            # Create indices for better query performance
            # User interactions collection
            user_interactions = db["user_interactions"]
            user_interactions.create_index("timestamp")
            user_interactions.create_index("session_id")
            
            # Agent responses collection
            agent_responses = db["agent_responses"]
            agent_responses.create_index("interaction_id")
            agent_responses.create_index("timestamp")
            agent_responses.create_index("agent_type")
            
            # System events collection
            system_events = db["system_events"]
            system_events.create_index("timestamp")
            system_events.create_index("event_type")
            
            # Errors collection
            errors = db["errors"]
            errors.create_index("timestamp")
            errors.create_index("interaction_id")
            
            # Insights collection
            insights = db["insights"]
            insights.create_index("timestamp")
            insights.create_index("insight_type")
            insights.create_index("applied")
            
            logger.debug("MongoDB collections and indices initialized")
            
        except Exception as e:
            logger.error(f"Error initializing MongoDB: {e}")
            raise
    
    def log_user_input(self, input_text: str, session_id: Optional[str] = None, 
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Log a user input interaction
        
        Args:
            input_text (str): The user's input text
            session_id (Optional[str]): Identifier for the user session
            metadata (Optional[Dict]): Additional metadata about the interaction
            
        Returns:
            str: The ID of the inserted interaction
        """
        collection = self._get_collection("user_interactions")
        
        document = {
            "timestamp": datetime.now().isoformat(),
            "input_text": input_text,
            "session_id": session_id,
            "metadata": metadata
        }
        
        result = collection.insert_one(document)
        interaction_id = str(result.inserted_id)
        
        logger.debug(f"Logged user input with ID {interaction_id}")
        return interaction_id
    
    def log_agent_response(self, query: str, response: str, agent_type: str, 
                          metadata: Optional[Dict[str, Any]] = None,
                          session_id: Optional[str] = None) -> str:
        """
        Log an agent's response to a user query
        
        Args:
            query (str): The user's original query
            response (str): The agent's response text
            agent_type (str): The type of agent that generated the response
            metadata (Optional[Dict]): Additional metadata about the response
            session_id (Optional[str]): Identifier for the user session
            
        Returns:
            str: The ID of the inserted response
        """
        user_collection = self._get_collection("user_interactions")
        response_collection = self._get_collection("agent_responses")
        
        # Look for the most recent matching query
        query_doc = user_collection.find_one(
            {"input_text": query},
            sort=[("timestamp", -1)]
        )
        
        if query_doc:
            interaction_id = str(query_doc["_id"])
        else:
            # If not found, create a new user interaction
            interaction_id = self.log_user_input(query, session_id)
        
        document = {
            "interaction_id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "response_text": response,
            "agent_type": agent_type,
            "metadata": metadata
        }
        
        result = response_collection.insert_one(document)
        response_id = str(result.inserted_id)
        
        logger.debug(f"Logged agent response with ID {response_id}")
        return response_id
    
    def log_system_event(self, event_type: str, description: str, 
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Log a system event
        
        Args:
            event_type (str): The type of system event
            description (str): Description of the event
            metadata (Optional[Dict]): Additional metadata about the event
            
        Returns:
            str: The ID of the inserted event
        """
        collection = self._get_collection("system_events")
        
        document = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "description": description,
            "metadata": metadata
        }
        
        result = collection.insert_one(document)
        event_id = str(result.inserted_id)
        
        logger.debug(f"Logged system event with ID {event_id}")
        return event_id
    
    def log_error(self, error_message: str, stack_trace: Optional[str] = None, 
                 agent_type: Optional[str] = None, query: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Log an error that occurred in the system
        
        Args:
            error_message (str): The error message
            stack_trace (Optional[str]): Stack trace of the error
            agent_type (Optional[str]): The type of agent that encountered the error
            query (Optional[str]): The user query that led to the error
            metadata (Optional[Dict]): Additional metadata about the error
            
        Returns:
            str: The ID of the inserted error
        """
        error_collection = self._get_collection("errors")
        user_collection = self._get_collection("user_interactions")
        
        # Find interaction ID if query is provided
        interaction_id = None
        if query:
            query_doc = user_collection.find_one(
                {"input_text": query},
                sort=[("timestamp", -1)]
            )
            if query_doc:
                interaction_id = str(query_doc["_id"])
        
        document = {
            "timestamp": datetime.now().isoformat(),
            "error_message": error_message,
            "stack_trace": stack_trace,
            "agent_type": agent_type,
            "interaction_id": interaction_id,
            "metadata": metadata
        }
        
        result = error_collection.insert_one(document)
        error_id = str(result.inserted_id)
        
        logger.debug(f"Logged error with ID {error_id}")
        return error_id
    
    def log_insight(self, insight_type: str, content: str, source: Optional[str] = None,
                   applied: bool = False, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Log an insight generated by the system's self-improvement mechanisms
        
        Args:
            insight_type (str): The type of insight (e.g., 'prompt_improvement', 'workflow_suggestion')
            content (str): The content of the insight
            source (Optional[str]): Source of the insight (e.g., 'memory_analysis')
            applied (bool): Whether the insight has been applied to the system
            metadata (Optional[Dict]): Additional metadata about the insight
            
        Returns:
            str: The ID of the inserted insight
        """
        collection = self._get_collection("insights")
        
        document = {
            "timestamp": datetime.now().isoformat(),
            "insight_type": insight_type,
            "content": content,
            "source": source,
            "applied": applied,
            "metadata": metadata
        }
        
        result = collection.insert_one(document)
        insight_id = str(result.inserted_id)
        
        logger.debug(f"Logged insight with ID {insight_id}")
        return insight_id
    
    def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent user interactions with responses
        
        Args:
            limit (int): Maximum number of interactions to retrieve
            
        Returns:
            List[Dict]: List of recent interactions with responses
        """
        user_collection = self._get_collection("user_interactions")
        response_collection = self._get_collection("agent_responses")
        
        # Get recent user interactions
        recent_interactions = list(
            user_collection.find().sort("timestamp", -1).limit(limit)
        )
        
        results = []
        
        # For each interaction, find the corresponding response
        for interaction in recent_interactions:
            interaction_id = str(interaction["_id"])
            
            # Convert MongoDB ObjectId to string for the output
            interaction["_id"] = interaction_id
            
            # Find corresponding response
            response = response_collection.find_one(
                {"interaction_id": interaction_id},
                sort=[("timestamp", -1)]
            )
            
            interaction_data = {
                "interaction_id": interaction_id,
                "interaction_time": interaction["timestamp"],
                "input_text": interaction["input_text"],
                "session_id": interaction.get("session_id"),
                "response_text": response.get("response_text") if response else None,
                "agent_type": response.get("agent_type") if response else None,
                "response_time": response.get("timestamp") if response else None
            }
            
            results.append(interaction_data)
        
        return results
    
    def close(self):
        """Close all database connections"""
        if hasattr(self._local, 'client'):
            self._local.client.close()
            del self._local.client
            logger.debug("MongoDB connection closed")
