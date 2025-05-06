"""
Base Tool Class for CPAS Agents
"""
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """Base class for all tools that agents can use"""
    
    def __init__(self, tool_id: str, name: str, description: str):
        """Initialize a base tool
        
        Args:
            tool_id: Unique identifier for this tool
            name: Display name for the tool
            description: Description of tool capabilities
        """
        self.tool_id = tool_id
        self.name = name
        self.description = description
        logger.info(f"Initialized tool: {name} ({tool_id})")
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the given parameters
        
        Args:
            params: Parameters for tool execution
            
        Returns:
            Result of tool execution
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation
        
        Returns:
            Dictionary of tool properties
        """
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description
        }
