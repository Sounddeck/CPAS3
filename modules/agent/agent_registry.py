"""
Agent Registry for CPAS
Registers available agent types
"""
import logging
from typing import Dict, Type

from modules.agent.agent_manager import agent_manager
from modules.agent.agents.base_agent import BaseAgent
from modules.agent.agents.conversation_agent import ConversationAgent

logger = logging.getLogger(__name__)

def register_agents():
    """Register all available agent types with the agent manager"""
    # Register conversation agent
    agent_manager.register_agent_class("conversation_agent", ConversationAgent)
    
    logger.info("Registered standard agent types")

# Register agents when this module is imported
register_agents()
