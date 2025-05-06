"""
Simple agent implementation for CPAS3
Uses direct LLM calls instead of ReAct
"""
import os
import logging
from typing import List, Dict, Any, Optional
import traceback

# LangChain imports
try:
    from langchain_ollama import OllamaLLM
    ollama_source = "langchain_ollama"
except ImportError:
    try:
        from langchain_community.llms import Ollama as OllamaLLM
        ollama_source = "langchain_community"
    except ImportError:
        from langchain.llms import Ollama as OllamaLLM
        ollama_source = "langchain"

# Template and other imports
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Local imports
from src.memory.simple_memory import SimpleMemory
from src.memory.structured_memory import StructuredMemory
from src.tools.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class SimpleAgent:
    """
    Simple LLM Agent implementation
    Uses OllamaLLM directly with LLMChain instead of ReAct agent
    """
    
    def __init__(
        self,
        model_name: str = "llama3",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        structured_memory: Optional[StructuredMemory] = None,
        tool_manager: Optional[ToolManager] = None,
        mongo_uri: str = "mongodb://localhost:27017/",
        session_id: str = "default"
    ):
        """
        Initialize the SimpleAgent
        
        Args:
            model_name (str): Ollama model name
            base_url (str): Ollama API URL
            temperature (float): Temperature for model sampling
            structured_memory (StructuredMemory): Memory storage instance
            tool_manager (ToolManager): Tool management instance
            mongo_uri (str): MongoDB connection URI
            session_id (str): Session identifier
        """
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.structured_memory = structured_memory
        self.tool_manager = tool_manager
        self.mongo_uri = mongo_uri
        self.session_id = session_id
        
        # Setup components
        self._setup_llm()
        self._setup_memory()
        self._setup_chain()
        
        logger.info(f"SimpleAgent initialized with model '{model_name}'")
    
    def _setup_llm(self):
        """Configure the LLM using Ollama"""
        try:
            # Use the appropriate parameters based on the import source
            if ollama_source == "langchain_ollama":
                self.llm = OllamaLLM(
                    model=self.model_name,
                    url=self.base_url,
                    temperature=self.temperature
                )
            else:
                self.llm = OllamaLLM(
                    model=self.model_name,
                    base_url=self.base_url,
                    temperature=self.temperature
                )
                
            logger.debug(f"Connected to Ollama at {self.base_url} using model {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LLM: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _setup_memory(self):
        """Configure conversation memory"""
        # Use SimpleMemory for conversation history
        self.conversation_memory = SimpleMemory(
            connection_uri=self.mongo_uri,
            db_name="cpas3_memory",
            collection_name="simple_chat_history",
            session_id=self.session_id
        )
        
        logger.debug(f"SimpleMemory initialized for session {self.session_id}")
    
    def _setup_chain(self):
        """Create and configure the LLM chain"""
        try:
            # Create a basic prompt
            template = """You are CPAS3, a Cognitive Processing Automation System, an intelligent assistant designed to help with a wide range of tasks.

Chat History:
{chat_history}

User: {input}

CPAS3 (helpful, concise, and accurate):"""
            
            prompt = PromptTemplate(
                input_variables=["chat_history", "input"],
                template=template
            )
            
            # Create LLM chain
            self.chain = LLMChain(
                llm=self.llm,
                prompt=prompt,
                verbose=True
            )
            
            logger.info("SimpleAgent chain setup complete")
            
        except Exception as e:
            logger.error(f"Error creating agent chain: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def run(self, query: str) -> Dict[str, Any]:
        """
        Run the agent with a user query
        
        Args:
            query (str): User input query
            
        Returns:
            Dict[str, Any]: Response with answer and metadata
        """
        logger.debug(f"Processing query: {query}")
        
        try:
            # Log the query to structured memory if available
            if self.structured_memory:
                try:
                    self.structured_memory.log_user_input(query)
                except Exception as e:
                    logger.error(f"Error logging to structured memory: {e}")
            
            # Add the user message to conversation memory
            self.conversation_memory.add_user_message(query)
            
            # Get chat history
            chat_history = self.conversation_memory.get_chat_history_as_string()
            
            # Run the LLM chain
            result = self.chain.invoke({
                "input": query,
                "chat_history": chat_history
            })
            
            # Extract response
            response = result.get("text", "")
            
            # Add the AI response to conversation memory
            self.conversation_memory.add_ai_message(response)
            
            # Log the result to structured memory if available
            if self.structured_memory:
                try:
                    self.structured_memory.log_agent_response(
                        query=query,
                        response=response,
                        agent_type="SimpleAgent",
                        metadata={"model": self.model_name}
                    )
                except Exception as e:
                    logger.error(f"Error logging response to structured memory: {e}")
            
            # Return response
            return {
                "response": response
            }
            
        except Exception as e:
            error_msg = f"Error running SimpleAgent: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # Log the error to structured memory if available
            if self.structured_memory:
                try:
                    self.structured_memory.log_error(
                        query=query,
                        error_message=str(e),
                        agent_type="SimpleAgent"
                    )
                except Exception as log_error:
                    logger.error(f"Error logging error to structured memory: {log_error}")
            
            return {
                "response": f"I encountered an error: {str(e)}",
                "error": str(e)
            }
