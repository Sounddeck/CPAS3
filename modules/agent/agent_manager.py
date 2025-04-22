import logging
import os
import uuid
import threading
from typing import List, Dict, Optional, Any, Type

# LangChain components
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate # Correct import if using directly
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_community.tools import DuckDuckGoSearchRun

# Attempt to import specific LLM providers, fall back if necessary
try:
    from langchain_ollama.chat_models import ChatOllama
except ImportError:
    logging.warning("langchain_ollama not found, falling back to langchain_community.ChatOllama.")
    try:
        from langchain_community.chat_models import ChatOllama
    except ImportError:
        logging.error("ChatOllama not found in langchain_community either. Ollama support disabled.")
        ChatOllama = None

try:
    # Conditional import for OpenAI if needed in the future
    # from langchain_openai import ChatOpenAI
    pass
except ImportError:
    logging.warning("langchain_openai not found. OpenAI support disabled.")
    # ChatOpenAI = None


# Local imports
from .agent_instance import AgentInstance
from .models import AgentStatus, AgentTask, AgentConfig
from .task_queue import TaskQueue
from .persistence.agent_store import AgentStore
from ..utils.config_manager import ConfigManager
from ..utils.history_manager import HistoryManager
from ..tools.tool_manager import ToolManager
from ..tools.file_system_tool import FileSystemTool
from .monitoring.resource_monitor import ResourceMonitor
from .monitoring.performance_tracker import PerformanceTracker

# Import the shared signal emitter
try:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT_FROM_AGENT_MANAGER = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))
    import sys
    if PROJECT_ROOT_FROM_AGENT_MANAGER not in sys.path:
        sys.path.insert(0, PROJECT_ROOT_FROM_AGENT_MANAGER)
    from modules.ui.signal_emitter import signal_emitter
    UI_AVAILABLE = True
except ImportError as e:
    UI_AVAILABLE = False
    class DummySignalEmitter:
        def __getattr__(self, name):
            class DummySignal:
                def emit(self, *args, **kwargs): pass
            return DummySignal()
    signal_emitter = DummySignalEmitter()
    logging.info(f"AgentManager running without UI signal emitter (ImportError: {e}).")


logger = logging.getLogger(__name__)

SCRIPT_DIR_AM = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_AM = os.path.abspath(os.path.join(SCRIPT_DIR_AM, '..', '..'))

class AgentManager:
    """
    Manages the lifecycle and task assignment for multiple AgentInstances.
    """
    def __init__(self, config_manager: ConfigManager):
        logger.info("Initializing AgentManager...")
        self.config_manager = config_manager
        self._task_queue = TaskQueue()
        self._agent_store = AgentStore(data_dir=config_manager.config_dir)
        self._history_manager = HistoryManager(save_callback=self._agent_store.save_agent_history)
        self._resource_monitor = ResourceMonitor()
        self._performance_tracker = PerformanceTracker()
        self.agents: Dict[str, AgentInstance] = {}
        self._agent_threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

        self.default_agent_config = self._load_default_agent_config()
        self.llm = self._initialize_llm()
        self.tool_manager = self._initialize_tool_manager()
        self.available_tools = self.tool_manager.get_tools()

        self.load_agents()
        self._resource_monitor.start()
        logger.info("AgentManager initialized.")

    def _load_default_agent_config(self) -> AgentConfig:
        """Loads the default agent configuration from ConfigManager."""
        default_agent_settings = {
            "max_iterations": 15, "temperature": 0.7, "verbose": True,
            "handle_parsing_errors": True, "early_stopping_method": "generate",
            "auto_start": True, "default_prompt": "You are a helpful assistant."
        }
        try:
            agent_defaults_data = self.config_manager.get("agent_defaults", default_agent_settings)
            if not isinstance(agent_defaults_data, dict):
                 logger.warning(f"Config key 'agent_defaults' not a dict. Using hardcoded defaults. Value: {agent_defaults_data}")
                 agent_defaults_data = default_agent_settings
            config = AgentConfig(**agent_defaults_data)
            logger.info(f"Loaded agent default config: {config.model_dump()}")
            return config
        except Exception as e:
            logger.error(f"Failed to load/parse default agent config: {e}. Using model defaults.", exc_info=True)
            return AgentConfig()

    def _initialize_llm(self) -> Optional[BaseChatModel]:
        """Initializes the language model based on configuration."""
        llm_provider = self.config_manager.get("llm_provider", "ollama")
        llm_model_name = self.config_manager.get("llm_model")
        llm_base_url = self.config_manager.get("llm_base_url")
        logger.info(f"Attempting to initialize LLM provider: {llm_provider}")
        if llm_provider == "ollama":
            # ... (rest of ollama init logic remains the same) ...
            if not ChatOllama:
                logger.error("Ollama provider selected but ChatOllama class is not available.")
                return None
            if not llm_model_name:
                llm_model_name = "mistral:7b"
                logger.warning(f"Ollama model not specified in config, defaulting to {llm_model_name}.")
            if not llm_base_url:
                 llm_base_url = "http://localhost:11434"
                 logger.info(f"Ollama base_url not specified in config, defaulting to {llm_base_url}")
            try:
                temperature = self.default_agent_config.temperature
                llm = ChatOllama(model=llm_model_name, base_url=llm_base_url, temperature=temperature)
                logger.info(f"Initialized ChatOllama with model '{llm_model_name}' at {llm_base_url}, temp={temperature}")
                return llm
            except AttributeError as e:
                 logger.error(f"CRITICAL: Error accessing temperature from default_agent_config: {e}. Check AgentConfig model and loading.", exc_info=True)
                 return None
            except Exception as e:
                logger.error(f"Failed to initialize ChatOllama: {e}", exc_info=True)
                return None
        else:
            logger.error(f"Unsupported LLM provider configured: {llm_provider}")
            return None


    def _initialize_tool_manager(self) -> ToolManager:
        """Initializes the ToolManager and registers tools."""
        workspace_base_dir = os.path.join(self.config_manager.config_dir, "agent_workspace")
        os.makedirs(workspace_base_dir, exist_ok=True)
        logger.info(f"ToolManager workspace base directory set to: {workspace_base_dir}")
        tool_manager = ToolManager(workspace_dir=workspace_base_dir)
        tool_classes_to_register: List[Type[BaseTool]] = [ FileSystemTool, DuckDuckGoSearchRun ]
        for tool_class in tool_classes_to_register:
            try:
                tool_manager.register_tool_class(tool_class)
            except Exception as e:
                logger.error(f"Failed to register tool class {tool_class.__name__}: {e}", exc_info=True)
        initialized_tools_dict = tool_manager.get_tools()
        logger.info(f"ToolManager initialized with tools: {list(initialized_tools_dict.keys())}")
        return tool_manager

    def _create_agent_executor(self, tools: List[BaseTool]) -> Optional[AgentExecutor]:
        """Creates a LangChain AgentExecutor."""
        if not self.llm: logger.error("Cannot create AgentExecutor: LLM not initialized."); return None
        if not tools: logger.warning("Cannot create AgentExecutor: No tools provided."); return None
        try:
            from langchain import hub
            prompt = hub.pull("hwchase17/react")
            logger.info("Loaded ReAct prompt 'hwchase17/react' from LangChain Hub.")
            agent = create_react_agent(self.llm, tools, prompt)
            agent_executor = AgentExecutor(
                agent=agent, tools=tools, verbose=self.default_agent_config.verbose,
                handle_parsing_errors=self.default_agent_config.handle_parsing_errors,
                max_iterations=self.default_agent_config.max_iterations
            )
            logger.info(f"Created AgentExecutor with tools: {[tool.name for tool in tools]}")
            return agent_executor
        except Exception as e:
            logger.error(f"Failed to create AgentExecutor: {e}", exc_info=True)
            return None

    def create_agent(
        self, name: str, config_overrides: Optional[Dict[str, Any]] = None,
        auto_start: bool = True # Kept for direct override
        ) -> Optional[AgentInstance]:
        """Creates, stores, and starts a new AgentInstance."""
        if not self.llm: logger.error("Cannot create agent: LLM not initialized."); return None
        if not self.available_tools: logger.warning("Cannot create agent: No tools available."); return None

        logger.info(f"Creating new agent: '{name}'")
        agent_id = uuid.uuid4().hex
        final_config = self.default_agent_config.model_copy(deep=True)
        if config_overrides:
            try:
                update_data = final_config.model_dump(); update_data.update(config_overrides)
                final_config = AgentConfig(**update_data)
                logger.info(f"Applied config overrides for new agent {agent_id[:8]}")
            except Exception as e:
                logger.error(f"Invalid config overrides for '{name}': {e}. Using defaults.", exc_info=True)
                final_config = self.default_agent_config.model_copy(deep=True)

        agent_tools = list(self.available_tools.values())
        agent_executor = self._create_agent_executor(agent_tools)
        if not agent_executor: logger.error(f"Failed AgentExecutor creation for '{name}'. Cannot create agent."); return None

        try:
            initial_status = AgentStatus.IDLE if final_config.auto_start else AgentStatus.STOPPED
            agent_instance = AgentInstance(
                agent_id=agent_id, name=name, config=final_config, llm=self.llm, tools=agent_tools,
                agent_executor=agent_executor, task_queue=self._task_queue, agent_store=self._agent_store,
                history_manager=self._history_manager, initial_status=initial_status,
                on_stop_callback=self._handle_agent_thread_stop
            )
        except Exception as e: logger.error(f"Failed AgentInstance init for '{name}': {e}", exc_info=True); return None

        with self._lock: self.agents[agent_id] = agent_instance
        try:
            self._agent_store.save_agent_state(agent_id, agent_instance.get_state())
            self._agent_store.add_agent_to_manifest(agent_id, name)
        except Exception as e: logger.error(f"Failed save state/manifest for agent {agent_id[:8]}: {e}", exc_info=True)

        logger.info(f"Agent '{name}' (ID: {agent_id[:8]}) created successfully with status {initial_status.name}.")
        signal_emitter.agent_created.emit(agent_instance.get_state())

        if final_config.auto_start:
            logger.info(f"Auto-starting new agent {agent_id[:8]} based on config.")
            try: agent_instance.start()
            except Exception as e:
                 logger.error(f"Failed start agent '{name}' post-creation: {e}", exc_info=True)
                 agent_instance._set_status(AgentStatus.ERROR)
        return agent_instance

    def load_agents(self):
        """Loads agent states from the AgentStore and recreates instances."""
        if not self.llm or not self.available_tools: logger.error("Cannot load agents: LLM or tools not initialized."); return
        logger.info("Loading agents from store...")
        try:
            agent_states = self._agent_store.get_all_agent_states()
            if not agent_states: logger.info("No existing agent states found."); return
            logger.info(f"Attempting load state for {len(agent_states)} agents...")
            loaded_count = 0
            agent_tools = list(self.available_tools.values())
            for agent_id, state_data in agent_states.items():
                if not state_data: logger.warning(f"No state data for ID {agent_id[:8]}. Skipping."); continue
                if agent_id in self.agents: logger.warning(f"Agent {agent_id[:8]} already in memory. Skipping."); continue
                agent_executor = self._create_agent_executor(agent_tools)
                if not agent_executor: logger.error(f"Failed AgentExecutor creation for loaded agent {agent_id[:8]}. Cannot load."); continue
                try:
                    instance = AgentInstance.from_state(
                        state_data=state_data, llm=self.llm, tools=agent_tools, agent_executor=agent_executor,
                        task_queue=self._task_queue, agent_store=self._agent_store, history_manager=self._history_manager,
                        on_stop_callback=self._handle_agent_thread_stop
                    )
                    if instance:
                        with self._lock: self.agents[agent_id] = instance
                        loaded_count += 1
                        logger.info(f"Agent '{instance.name}' (ID: {agent_id[:8]}) loaded with status {instance.status.name}.")
                        if instance.config.auto_start and instance.status not in [AgentStatus.STOPPED, AgentStatus.ERROR]:
                            logger.info(f"Auto-starting loaded agent {agent_id[:8]}...")
                            try: instance.start()
                            except Exception as e:
                                logger.error(f"Failed auto-start loaded agent {agent_id[:8]}: {e}", exc_info=True)
                                instance._set_status(AgentStatus.ERROR)
                        else:
                            logger.info(f"Agent {agent_id[:8]} not auto-starting (auto_start={instance.config.auto_start}, status={instance.status.name}).")
                    else: logger.error(f"Failed recreate instance from state for ID {agent_id[:8]}.")
                except Exception as e: logger.error(f"Error loading agent {agent_id[:8]} from state: {e}", exc_info=True)
            logger.info(f"Finished loading {loaded_count} agents.")
        except Exception as e: logger.error(f"Failed load agents from store: {e}", exc_info=True)

    def remove_agent(self, agent_id: str):
        """Stops, removes, and cleans up an agent."""
        logger.info(f"Removing agent {agent_id[:8]}...")
        instance = self.get_agent(agent_id)
        if not instance: logger.warning(f"Agent {agent_id[:8]} not found for removal."); return
        try: instance.stop()
        except Exception as e: logger.error(f"Error signaling stop for agent {agent_id[:8]}: {e}", exc_info=True)
        try: instance.cleanup()
        except Exception as e: logger.error(f"Error during cleanup for agent {agent_id[:8]}: {e}", exc_info=True)
        with self._lock:
            if agent_id in self.agents: del self.agents[agent_id]
            if agent_id in self._agent_threads: del self._agent_threads[agent_id]
        try:
            self._agent_store.remove_agent_state(agent_id)
            self._agent_store.remove_agent_history(agent_id)
            self._agent_store.remove_agent_from_manifest(agent_id)
            logger.info(f"Removed agent {agent_id[:8]} state/manifest.")
        except Exception as e: logger.error(f"Error removing agent {agent_id[:8]} from store: {e}", exc_info=True)
        logger.info(f"Agent {agent_id[:8]} removed.")
        signal_emitter.agent_removed.emit(agent_id)

    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        with self._lock: return self.agents.get(agent_id)

    def get_all_agents(self) -> List[AgentInstance]:
        with self._lock: return list(self.agents.values())

    def assign_task(self, task: AgentTask) -> bool:
        """Adds a task to the central queue."""
        try:
            self._task_queue.put(task)
            logger.info(f"Task {task.task_id[:8]} added to queue. Desc: '{task.description[:50]}...'")
            signal_emitter.task_created.emit(task.to_dict())
            return True
        except Exception as e:
            logger.error(f"Failed add task {task.task_id[:8]} to queue: {e}", exc_info=True)
            return False

    def _handle_agent_thread_stop(self, agent_id: str):
         """Callback executed when an agent's execution thread finishes."""
         logger.info(f"Manager notified: Agent {agent_id[:8]}'s thread stopped.")
         with self._lock:
              if agent_id in self._agent_threads: del self._agent_threads[agent_id]
         agent = self.get_agent(agent_id)
         if agent and agent.status not in [AgentStatus.STOPPED, AgentStatus.ERROR]:
              logger.warning(f"Agent {agent_id[:8]} thread stopped unexpectedly (status: {agent.status.name}). Setting ERROR.")
              agent._set_status(AgentStatus.ERROR)

    def shutdown(self):
        """Shuts down all agents and monitoring."""
        logger.info("Shutting down AgentManager...")
        self._resource_monitor.stop()
        agents_to_stop = self.get_all_agents()
        logger.info(f"Stopping {len(agents_to_stop)} agents...")
        for agent in agents_to_stop:
            try:
                 logger.info(f"Requesting stop for agent {agent.id[:8]}...")
                 agent.stop()
            except Exception as e:
                 # *** CORRECTED LOGGING LINE ***
                 logger.error(f"Error signaling stop for agent {agent.id[:8]}: {e}", exc_info=True)
        logger.info("AgentManager shutdown complete.")

