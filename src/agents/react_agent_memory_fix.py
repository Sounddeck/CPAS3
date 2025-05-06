"""
Quick fix for ReAct agent to handle memory issues
"""

import logging
from src.agents.react_agent import ReActAgent

logger = logging.getLogger(__name__)

# Create a patch method for the run function
def patched_run(self, query: str):
    """
    Patched version of the run method that handles memory issues
    """
    try:
        # Try to run with memory
        return self.original_run(query)
    except AttributeError as e:
        if "'MongoChatMemory' object has no attribute 'memory_key'" in str(e):
            logger.warning("Memory key issue detected, falling back to no-memory execution")
            
            # Create a backup of current memory
            backup_memory = self.conversation_memory
            
            try:
                # Temporarily disable memory
                self.agent_executor.memory = None
                
                # Run without memory
                result = self.agent_executor.invoke({"input": query})
                
                # Return a processed result
                return {
                    "response": result.get("output", ""),
                    "intermediate_steps": result.get("intermediate_steps", []),
                    "memory_fallback": True
                }
            finally:
                # Restore memory
                self.agent_executor.memory = backup_memory
        else:
            # Re-raise other errors
            raise

# Apply the patch
def apply_memory_patch():
    """Apply the memory patch to the ReActAgent class"""
    logger.info("Applying memory patch to ReActAgent")
    ReActAgent.original_run = ReActAgent.run
    ReActAgent.run = patched_run
