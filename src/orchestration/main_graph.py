"""
Main LangGraph orchestration for CPAS3
Defines the execution flow between components
"""
import logging
from typing import Dict, Any, List, Optional
import traceback

# Local imports
from src.agents.react_agent import ReActAgent
from src.memory.structured_memory import StructuredMemory

logger = logging.getLogger(__name__)

class MainGraph:
    """
    Main LangGraph orchestration for CPAS3
    Simplified implementation that directly uses the ReAct agent
    """
    
    def __init__(
        self,
        react_agent: ReActAgent,
        structured_memory: Optional[StructuredMemory] = None,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "cpas3_langgraph"
    ):
        """
        Initialize the main orchestration graph
        
        Args:
            react_agent (ReActAgent): The ReAct agent instance
            structured_memory (Optional[StructuredMemory]): Structured memory instance
            mongo_uri (str): MongoDB connection URI (used for structured memory)
            db_name (str): Database name for memory (used for structured memory)
        """
        self.react_agent = react_agent
        self.structured_memory = structured_memory
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        
        logger.info("MainGraph initialized with in-memory checkpoint storage")
    
    def run(self, user_input: str) -> Dict[str, Any]:
        """
        Run the agent with a user query
        
        Args:
            user_input (str): The user's input query
            
        Returns:
            Dict[str, Any]: The final state
        """
        logger.info(f"Running graph with input: {user_input}")
        
        # Log to structured memory if available
        if self.structured_memory:
            try:
                self.structured_memory.log_user_input(user_input)
            except Exception as e:
                logger.error(f"Error logging to structured memory: {e}")
        
        try:
            # Directly use the ReAct agent
            result = self.react_agent.run(user_input)
            
            # Log the result to structured memory if available
            if self.structured_memory:
                try:
                    self.structured_memory.log_agent_response(
                        query=user_input,
                        response=result.get("response", ""),
                        agent_type="ReActAgent",
                        metadata={"status": "success"}
                    )
                except Exception as e:
                    logger.error(f"Error logging result to structured memory: {e}")
            
            # Create a response with the right format
            response = {
                "status": "success",
                "response": result.get("response", "No response generated"),
                "errors": [],
                "messages": [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": result.get("response", "No response generated")}
                ]
            }
            
            return response
            
        except Exception as e:
            error_msg = f"Error running agent: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # Log the error to structured memory if available
            if self.structured_memory:
                try:
                    self.structured_memory.log_error(
                        error_message=error_msg,
                        query=user_input,
                        agent_type="MainGraph"
                    )
                except Exception as mem_error:
                    logger.error(f"Error logging error to structured memory: {mem_error}")
            
            # Create a fallback response
            return {
                "status": "error",
                "error": str(e),
                "response": f"I encountered an error: {str(e)}",
                "messages": [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": f"I encountered an error: {str(e)}"}
                ],
                "errors": [str(e)]
            }
