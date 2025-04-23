"""
Agent Module Initialization
---------------------------

This module provides the core components for creating, managing, and running autonomous agents
within the CPAS framework.

Key Components:
- BaseAgent: Abstract base class for all agent implementations.
- AgentStatus: Enum defining possible agent states.
- AgentManager: Manages the lifecycle (creation, loading, saving, running) of multiple agents.
- Task: Represents a unit of work to be performed by an agent.
- TaskStatus: Enum defining possible task states.
- TaskQueue: Manages the queue of tasks for agents.
- CallbackManager: Handles Langchain callbacks for logging, UI updates, etc.
- AgentStore: Handles persistence of agent configurations and states.
- ToolManager: Discovers and manages tools available to agents.

Example Usage:

from modules.agent import AgentManager, Task

# Assuming llm and tools are defined elsewhere
manager = AgentManager()
manager.create_agent(
    agent_type="TaskAgent",
    name="My First Agent",
    llm=my_llm_instance,
    # tools=my_tools_list # Tools usually managed internally now
    description="An agent to perform specific tasks."
)

manager.add_task(Task(description="Summarize the provided text.", data={"text": "..."}))
manager.start_all_agents()

# ... later ...
manager.stop_all_agents()

"""

import logging

# Configure logger for the module if needed, or rely on global config
# logger = logging.getLogger(__name__)
# logger.addHandler(logging.NullHandler()) # Avoids "No handler found" warnings if not configured elsewhere

# --- Core Agent Components ---
from .base_agent import BaseAgent, AgentStatus
from .agent_manager import AgentManager

# --- Task Management ---
from .task_queue import Task, TaskStatus, TaskQueue

# --- Persistence ---
from .persistence.agent_store import AgentStore

# --- Callbacks ---
from .callback_manager import CallbackManager, AgentCallbackHandler

# --- Tools (Expose the manager, specific tools accessed via manager) ---
from .tools.tool_manager import ToolManager
# Optionally expose specific tool classes if they need direct access often
# from .tools.file_tool import FileSystemTool
# from .tools.shell_tool import ShellTool
# from .tools.web_tool import WebBrowserTool

# --- Specific Agent Implementations (Expose if needed for direct instantiation) ---
from .agents.task_agent import TaskAgent
# from .agents.search_agent import SearchAgent # If you have others

# --- Define what gets imported with "from modules.agent import *" ---
# It's generally better practice to import specific names, but __all__ defines the wildcard behavior.
__all__ = [
    "BaseAgent",
    "AgentStatus",
    "AgentManager",
    "Task",
    "TaskStatus",
    "TaskQueue",
    "AgentStore",
    "CallbackManager",
    "AgentCallbackHandler",
    "ToolManager",
    "TaskAgent",
    # Add other exposed classes/functions here if needed
    # "SearchAgent",
    # "FileSystemTool",
    # "ShellTool",
    # "WebBrowserTool",
]

logging.getLogger(__name__).info("Agent module initialized.")

