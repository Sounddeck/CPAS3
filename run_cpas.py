import os
import sys
import logging
import time # <<< ADDED: Import time >>>

# --- Configure logging ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Get the root logger
root_logger = logging.getLogger()

# --- Now import your modules ---
from modules.agents.agent_manager import AgentManager
from modules.tools.file_system_tool import FileSystemTool
# <<< CORRECTED: Import Task class from 'agents' (plural) >>>
from modules.agents.task_queue import Task

# --- Constants ---
WORKSPACE_DIR = os.path.join(os.path.expanduser("~"), ".cpas3", "workspace")
AGENT_STATE_DIR = os.path.join(os.path.expanduser("~"), ".cpas3", "agents")
MEMORY_DB_PATH = os.path.join(os.path.expanduser("~"), ".cpas3", "cpas_memory.db")

# --- Main Execution ---
if __name__ == "__main__":
    # Ensure workspace directory exists
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        root_logger.info(f"Workspace directory ensured at: {WORKSPACE_DIR}")
    except OSError as e:
        root_logger.error(f"Failed to create workspace directory {WORKSPACE_DIR}: {e}", exc_info=True)
        sys.exit(1)

    # --- Tool Configuration ---
    tool_config = {
        "FileSystemTool": {
            "root_dir": WORKSPACE_DIR
        }
    }
    root_logger.info(f"Tool configurations prepared: {tool_config}")

    # --- Initialize Agent Manager ---
    root_logger.info("Initializing AgentManager...")
    try:
        agent_manager = AgentManager(
            agent_state_dir=AGENT_STATE_DIR,
            memory_db_path=MEMORY_DB_PATH,
            tool_config=tool_config
        )
        if agent_manager and agent_manager.tool_manager:
             root_logger.info("AgentManager initialization complete.")
             loaded_tools_list = agent_manager.tool_manager.get_all_tools()
             if loaded_tools_list:
                  root_logger.info(f"Tools loaded by AgentManager: {[tool.name for tool in loaded_tools_list]}")
             else:
                  root_logger.warning("AgentManager initialized, but ToolManager reported no loaded tools.")
        else:
             root_logger.error("AgentManager or its ToolManager failed to initialize properly. Exiting.")
             sys.exit(1)

    except Exception as e:
        root_logger.critical(f"Failed to initialize AgentManager: {e}", exc_info=True)
        sys.exit(1)

    # --- Create and add a test task ---
    try:
        if agent_manager and agent_manager.task_queue:
            task_description = "List all files and directories in the root of the workspace."
            new_task = Task(description=task_description)
            agent_manager.task_queue.add_task(new_task)
            root_logger.info(f"Added test task to queue: '{task_description}'")
        else:
            root_logger.error("Cannot add task: AgentManager or TaskQueue not available.")
    except Exception as e:
        root_logger.error(f"Failed to add test task: {e}", exc_info=True)

    # --- Original Placeholder/Loop ---
    root_logger.info("Application started successfully. Main loop running...")
    root_logger.info("Agents will now process tasks from the queue. (Ctrl+C to exit)")

    try:
        # The agent threads are running in the background (started by AgentManager).
        # This loop just keeps the main thread alive.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        root_logger.info("Shutdown requested (KeyboardInterrupt).")
    finally:
        # --- Shutdown ---
        if 'agent_manager' in locals() and agent_manager:
            root_logger.info("Shutting down AgentManager...")
            agent_manager.shutdown()
        root_logger.info("Application finished.")

