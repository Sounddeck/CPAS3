"""
Agent Manager for CPAS
Handles creation, loading and management of AI agents
"""
import os
import json
import logging
import importlib
from typing import Dict, List, Any, Optional, Type

from src.core.event_bus import event_bus
from modules.agent.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AgentManager:
    """Manages AI agents in the CPAS system"""
    
    def __init__(self):
        """Initialize the agent manager"""
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_classes: Dict[str, Type[BaseAgent]] = {}
        self.agent_config_dir = os.path.join("data", "agents")
        
        # Ensure config directory exists
        os.makedirs(self.agent_config_dir, exist_ok=True)
        
        # Register events
        event_bus.subscribe("module_unloaded", self._handle_module_unload)
        
        logger.info("Agent manager initialized")
    
    def register_agent_class(self, agent_type: str, agent_class: Type[BaseAgent]) -> None:
        """Register an agent class that can be instantiated
        
        Args:
            agent_type: Type identifier for this agent class
            agent_class: The agent class to register
        """
        self.agent_classes[agent_type] = agent_class
        logger.info(f"Registered agent class: {agent_type}")
    
    def create_agent(self, agent_type: str, agent_id: str, name: str, description: str, **kwargs) -> Optional[BaseAgent]:
        """Create a new agent
        
        Args:
            agent_type: Type of agent to create
            agent_id: Unique identifier for this agent
            name: Display name for the agent
            description: Description of agent capabilities
            **kwargs: Additional parameters for agent initialization
            
        Returns:
            The created agent or None if creation failed
        """
        if agent_id in self.agents:
            logger.warning(f"Agent with ID {agent_id} already exists")
            return None
        
        if agent_type not in self.agent_classes:
            logger.error(f"Unknown agent type: {agent_type}")
            return None
        
        try:
            # Create agent instance
            agent_class = self.agent_classes[agent_type]
            agent = agent_class(agent_id=agent_id, name=name, description=description, **kwargs)
            
            # Store agent
            self.agents[agent_id] = agent
            
            # Publish event
            event_bus.publish("agent_created", agent_id=agent_id, agent=agent)
            
            logger.info(f"Created agent: {name} ({agent_id})")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent {agent_id}: {e}")
            return None
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID
        
        Args:
            agent_id: ID of agent to retrieve
            
        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)
    
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent
        
        Args:
            agent_id: ID of agent to delete
            
        Returns:
            True if successful, False otherwise
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent with ID {agent_id} not found")
            return False
        
        # Stop agent if running
        agent = self.agents[agent_id]
        if agent.is_running:
            agent.stop()
        
        # Remove agent
        del self.agents[agent_id]
        
        # Publish event
        event_bus.publish("agent_deleted", agent_id=agent_id)
        
        logger.info(f"Deleted agent: {agent_id}")
        return True
    
    def start_agent(self, agent_id: str) -> bool:
        """Start an agent
        
        Args:
            agent_id: ID of agent to start
            
        Returns:
            True if successful, False otherwise
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent with ID {agent_id} not found")
            return False
        
        agent = self.agents[agent_id]
        agent.start()
        
        # Publish event
        event_bus.publish("agent_started", agent_id=agent_id)
        
        return True
    
    def stop_agent(self, agent_id: str) -> bool:
        """Stop an agent
        
        Args:
            agent_id: ID of agent to stop
            
        Returns:
            True if successful, False otherwise
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent with ID {agent_id} not found")
            return False
        
        agent = self.agents[agent_id]
        agent.stop()
        
        # Publish event
        event_bus.publish("agent_stopped", agent_id=agent_id)
        
        return True
    
    def save_agent(self, agent_id: str) -> bool:
        """Save agent configuration
        
        Args:
            agent_id: ID of agent to save
            
        Returns:
            True if successful, False otherwise
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent with ID {agent_id} not found")
            return False
        
        try:
            # Get agent data
            agent = self.agents[agent_id]
            agent_data = agent.to_dict()
            
            # Save to file
            config_path = os.path.join(self.agent_config_dir, f"{agent_id}.json")
            with open(config_path, 'w') as f:
                json.dump(agent_data, f, indent=2)
            
            logger.info(f"Saved agent configuration: {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save agent {agent_id}: {e}")
            return False
    
    def load_agents(self) -> int:
        """Load all saved agent configurations
        
        Returns:
            Number of agents loaded
        """
        if not os.path.exists(self.agent_config_dir):
            return 0
        
        count = 0
        for filename in os.listdir(self.agent_config_dir):
            if filename.endswith(".json"):
                try:
                    # Load config file
                    config_path = os.path.join(self.agent_config_dir, filename)
                    with open(config_path, 'r') as f:
                        agent_data = json.load(f)
                    
                    # Extract agent_id and agent_type
                    agent_id = agent_data.get("agent_id")
                    agent_type = agent_data.get("agent_type")
                    
                    if not agent_id or not agent_type:
                        logger.warning(f"Invalid agent config: {filename}")
                        continue
                    
                    # Create agent
                    if self.create_agent(
                        agent_type=agent_type,
                        agent_id=agent_id,
                        name=agent_data.get("name", agent_id),
                        description=agent_data.get("description", ""),
                        config=agent_data.get("config", {})
                    ):
                        count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to load agent from {filename}: {e}")
        
        logger.info(f"Loaded {count} agents")
        return count
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents
        
        Returns:
            List of agent details
        """
        return [agent.to_dict() for agent in self.agents.values()]
    
    def list_agent_types(self) -> Dict[str, str]:
        """List all available agent types
        
        Returns:
            Dictionary mapping agent type IDs to display names
        """
        return {agent_type: agent_class.__doc__ or agent_type 
                for agent_type, agent_class in self.agent_classes.items()}
    
    def _handle_module_unload(self, module_id: str) -> None:
        """Handle module unload event
        
        Args:
            module_id: ID of the module being unloaded
        """
        if module_id == "agent_module":
            # Stop all agents
            for agent_id, agent in list(self.agents.items()):
                if agent.is_running:
                    agent.stop()
                    logger.info(f"Stopped agent {agent_id} due to module unload")

# Create singleton instance
agent_manager = AgentManager()
