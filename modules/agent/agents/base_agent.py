"""
Base Agent Class for CPAS
"""
import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all CPAS agents"""
    
    def __init__(self, agent_id: str, name: str, description: str):
        """Initialize a base agent
        
        Args:
            agent_id: Unique identifier for this agent
            name: Display name for the agent
            description: Description of agent capabilities
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.is_running = False
        self.memory = {}
        self.tools = {}
        logger.info(f"Initialized agent: {name} ({agent_id})")
    
    def add_tool(self, tool_id: str, tool_instance: Any) -> None:
        """Add a tool to this agent
        
        Args:
            tool_id: Unique identifier for the tool
            tool_instance: Instance of the tool
        """
        self.tools[tool_id] = tool_instance
        logger.info(f"Added tool {tool_id} to agent {self.agent_id}")
    
    def remove_tool(self, tool_id: str) -> None:
        """Remove a tool from this agent
        
        Args:
            tool_id: ID of tool to remove
        """
        if tool_id in self.tools:
            del self.tools[tool_id]
            logger.info(f"Removed tool {tool_id} from agent {self.agent_id}")
    
    def start(self) -> None:
        """Start the agent"""
        if not self.is_running:
            self.is_running = True
            logger.info(f"Started agent: {self.agent_id}")
            self._on_start()
    
    def stop(self) -> None:
        """Stop the agent"""
        if self.is_running:
            self._on_stop()
            self.is_running = False
            logger.info(f"Stopped agent: {self.agent_id}")
    
    @abstractmethod
    def _on_start(self) -> None:
        """Called when agent is started"""
        pass
    
    @abstractmethod
    def _on_stop(self) -> None:
        """Called when agent is stopped"""
        pass
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process input data and return a response
        
        Args:
            input_data: Data to be processed
            
        Returns:
            Processed result
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation
        
        Returns:
            Dictionary of agent properties
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "is_running": self.is_running,
            "tools": list(self.tools.keys())
        }
