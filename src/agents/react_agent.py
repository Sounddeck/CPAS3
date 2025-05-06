"""
React Agent implementation for CPAS3
Uses Ollama for local LLM inference
"""
import os
import logging
from typing import List, Dict, Any, Optional

# LangChain imports - using the latest recommended imports
try:
    # Try to import from langchain_ollama first (recommended)
    from langchain_ollama import OllamaLLM
    ollama_import_source = "langchain_ollama"
except ImportError:
    try:
        # Then try langchain_community as fallback
        from langchain_community.llms import Ollama as OllamaLLM
        ollama_import_source = "langchain_community"
    except ImportError:
        # Finally, fallback to deprecated import
        from langchain.llms import Ollama as OllamaLLM
        ollama_import_source = "langchain"

# Agent imports
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage

# Local imports
from src.tools.tool_manager import ToolManager
from src.memory.structured_memory import StructuredMemory
from src.memory.mongo_memory import create_mongodb_memory

logger = logging.getLogger(__name__)

class ReActAgent:
    """
    ReAct (Reasoning + Acting) Agent for CPAS3
    Integrates Ollama with LangChain's ReAct agent and local tools
    """
    
    def __init__(
        self,
        model_name: str = "llama3",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        structured_memory: Optional[StructuredMemory] = None,
        tool_manager: Optional[ToolManager] = None,
        mongo_uri: str = "mongodb://localhost:27017/",
        session_id: str = "default"
    ):
        """
        Initialize the ReAct agent with Ollama and tools
        
        Args:
            model_name (str): Ollama model name
            base_url (str): Ollama API URL
            temperature (float): Temperature for model sampling
            structured_memory (StructuredMemory): Memory storage instance
            tool_manager (ToolManager): Tool management instance
            mongo_uri (str): MongoDB connection URI
            session_id (str): Session identifier for memory
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
        self._setup_agent()
        
        logger.info(f"ReActAgent initialized with model '{model_name}'")
    
    def _setup_llm(self):
        """Configure the LLM using Ollama"""
        try:
            # Use the imported OllamaLLM class with appropriate arguments
            # based on which package we're using
            if ollama_import_source == "langchain_ollama":
                self.llm = OllamaLLM(
                    model=self.model_name,
                    url=self.base_url,  # In langchain_ollama it's 'url', not 'base_url'
                    temperature=self.temperature
                )
            else:
                self.llm = OllamaLLM(
                    model=self.model_name,
                    base_url=self.base_url,
                    temperature=self.temperature
                )
            
            logger.debug(f"Connected to Ollama at {self.base_url} using model {self.model_name} via {ollama_import_source}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LLM: {e}")
            raise
    
    def _setup_memory(self):
        """Configure conversation memory"""
        # Use MongoDB-backed conversation memory
        self.conversation_memory = create_mongodb_memory(
            connection_uri=self.mongo_uri,
            db_name="cpas3_memory",
            collection_name="agent_chat_history",
            session_id=self.session_id,
            memory_key="chat_history",
            return_messages=True
        )
        logger.debug(f"MongoDB conversation memory initialized for session {self.session_id}")
    
    def _setup_agent(self):
        """Create and configure the ReAct agent"""
        # Get available tools
        tools = []
        if self.tool_manager:
            tools = self.tool_manager.get_all_tools()
            logger.debug(f"Loaded {len(tools)} tools from ToolManager")
        
        # Create a default fallback prompt if loading fails
        default_prompt = PromptTemplate.from_template(
            """You are CPAS3, a Cognitive Processing Automation System.
            You are a helpful assistant that uses tools to provide accurate and useful responses.
            
            Tools available: {tool_names}
            
            {tools}
            
            Use these tools to help answer the user's question.
            When you use a tool, carefully review the output before moving on.
            
            Chat History:
            {chat_history}
            
            User Question: {input}
            
            {agent_scratchpad}
            
            Respond in a helpful, informative, and conversational manner.
            Always provide accurate information and acknowledge when you don't know something.
            """
        )
        
        # Load custom prompt or use default
        try:
            # First check if the prompts directory exists
            if not os.path.exists("prompts"):
                os.makedirs("prompts")
            
            # Check for the prompt file
            prompt_path = os.path.join("prompts", "react_agent_prompt.py")
            if os.path.exists(prompt_path):
                # Import dynamic prompt
                import importlib.util
                spec = importlib.util.spec_from_file_location("prompt_module", prompt_path)
                prompt_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(prompt_module)
                prompt = prompt_module.REACT_AGENT_PROMPT
                logger.debug(f"Loaded custom prompt from {prompt_path}")
            else:
                # Create the prompt file with default content
                with open(prompt_path, "w") as f:
                    f.write('''"""
Default prompt template for the ReAct agent
"""
from langchain.prompts import PromptTemplate

# Default ReAct agent prompt template with all required variables
REACT_AGENT_PROMPT = PromptTemplate.from_template(
"""You are CPAS3, a Cognitive Processing Automation System.
You are a helpful assistant that uses tools to provide accurate and useful responses.

Tools available: {tool_names}

{tools}

Use these tools to help answer the user's question.
When you use a tool, carefully review the output before moving on.

Chat History:
{chat_history}

User Question: {input}

{agent_scratchpad}

Respond in a helpful, informative, and conversational manner.
Always provide accurate information and acknowledge when you don't know something.
"""
)
''')
                # Use default prompt for now
                prompt = default_prompt
                logger.debug("Created and using default ReAct agent prompt")
        except Exception as e:
            logger.warning(f"Error working with custom prompt, falling back to default: {e}")
            prompt = default_prompt
        
        # Create the agent with proper prompt
        try:
            self.agent = create_react_agent(
                llm=self.llm,
                tools=tools,
                prompt=prompt
            )
            
            # Create the executor
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=tools,
                memory=self.conversation_memory,
                verbose=True,
                handle_parsing_errors=True
            )
            
            logger.info("ReAct agent setup complete")
        except Exception as e:
            logger.error(f"Error creating ReAct agent: {e}")
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
                self.structured_memory.log_user_input(query)
            
            # Run the agent
            result = self.agent_executor.invoke({"input": query})
            
            # Log the result to structured memory if available
            if self.structured_memory:
                self.structured_memory.log_agent_response(
                    query=query,
                    response=result.get("output", ""),
                    agent_type="ReActAgent",
                    metadata={"model": self.model_name}
                )
            
            # Add any traces or intermediate steps
            return {
                "response": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", [])
            }
            
        except Exception as e:
            error_msg = f"Error running ReAct agent: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Still log the error to structured memory
            if self.structured_memory:
                self.structured_memory.log_error(
                    query=query,
                    error_message=str(e),
                    agent_type="ReActAgent"
                )
            
            return {
                "response": f"I encountered an error: {str(e)}",
                "error": str(e)
            }
