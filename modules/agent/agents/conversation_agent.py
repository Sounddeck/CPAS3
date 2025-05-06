"""
Conversation Agent for CPAS
Basic agent that can engage in conversation
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional
import json
import time

from modules.agent.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class ConversationAgent(BaseAgent):
    """Agent that can engage in conversation"""
    
    def __init__(self, agent_id: str, name: str, description: str, **kwargs):
        """Initialize a conversation agent
        
        Args:
            agent_id: Unique identifier for this agent
            name: Display name for the agent
            description: Description of agent capabilities
            **kwargs: Additional configuration options
        """
        super().__init__(agent_id, name, description)
        
        # Agent settings
        self.conversation_history = []
        self.settings = kwargs.get("config", {})
        self.personality = self.settings.get("personality", "helpful and friendly")
        
        # Default responses
        self.default_responses = [
            "I'm sorry, I didn't understand that. Could you rephrase?",
            "Interesting perspective. Can you tell me more?",
            "I'll need to think about that.",
            "Let me see if I can help with that.",
            "That's a good question. Let me consider it."
        ]
        
        # Response counter for simulating responses
        self._response_count = 0
    
    def _on_start(self) -> None:
        """Called when agent is started"""
        logger.info(f"Conversation agent started: {self.agent_id}")
    
    def _on_stop(self) -> None:
        """Called when agent is stopped"""
        logger.info(f"Conversation agent stopped: {self.agent_id}")
    
    async def process(self, input_data: Any) -> Any:
        """Process input data and return a response
        
        Args:
            input_data: Message from user
            
        Returns:
            Agent response
        """
        if not self.is_running:
            return {"error": "Agent is not running"}
        
        # Add to conversation history
        if isinstance(input_data, str):
            # Simple string message
            message = input_data
            self.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": time.time()
            })
        else:
            # Structured message
            message = input_data.get("content", "")
            self.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": time.time()
            })
        
        # Generate response - in a real implementation this would use an AI model
        response = await self._generate_response(message)
        
        # Add response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": time.time()
        })
        
        return {
            "content": response,
            "agent_id": self.agent_id,
            "timestamp": time.time()
        }
    
    async def _generate_response(self, message: str) -> str:
        """Generate a response to the user message
        
        Args:
            message: User message
            
        Returns:
            Agent response
        """
        # In a real implementation, this would call an AI model API
        # For now, just return a simple simulated response
        
        # Simulate some processing time
        await asyncio.sleep(0.5)
        
        # Simple keyword-based responses
        message_lower = message.lower()
        
        if "hello" in message_lower or "hi" in message_lower:
            return f"Hello! I'm {self.name}, your virtual assistant. How can I help you today?"
        
        if "how are you" in message_lower:
            return "I'm functioning optimally, thank you for asking! How may I assist you?"
        
        if "bye" in message_lower or "goodbye" in message_lower:
            return "Goodbye! Feel free to chat again anytime."
        
        if "thank" in message_lower:
            return "You're welcome! Is there anything else you'd like help with?"
        
        if "help" in message_lower:
            return f"I'd be happy to help! As {self.name}, I can assist with answering questions and engaging in conversation."
        
        # Cycle through default responses for other messages
        response = self.default_responses[self._response_count % len(self.default_responses)]
        self._response_count += 1
        
        return response
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history
        
        Returns:
            List of messages in the conversation
        """
        return self.conversation_history
    
    def clear_conversation(self) -> None:
        """Clear the conversation history"""
        self.conversation_history = []
        logger.info(f"Cleared conversation history for agent {self.agent_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation
        
        Returns:
            Dictionary of agent properties
        """
        base_dict = {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "is_running": self.is_running
        }
        base_dict.update({
            "agent_type": "conversation_agent",
            "personality": self.personality,
            "message_count": len(self.conversation_history)
        })
        return base_dict
