
import logging
import signal
import sys
import time
import os
from typing import Optional

# --- TEMPORARY DEBUGGING ---
# Let's try to read the problematic file directly before imports
try:
    base_tool_path = os.path.join(os.path.dirname(__file__), 'modules', 'tools', 'base_tool.py')
    if not os.path.exists(base_tool_path):
        print(f"DEBUG: Cannot find base_tool.py at expected path: {base_tool_path}")
    else:
        print(f"DEBUG: Reading lines from: {base_tool_path}")
        with open(base_tool_path, 'r') as f:
            lines = f.readlines()
        print("-" * 30)
        print("DEBUG: Content of base_tool.py around lines 78/79:")
        start_line = 75 # Line numbers are 0-indexed in lists, but errors are 1-indexed
        end_line = 82
        if len(lines) > start_line:
            for i in range(start_line, min(end_line + 1, len(lines))):
                 # Adding line number (1-based) for clarity
                print(f"  Line {i+1}: {lines[i].rstrip()}") # rstrip removes trailing newline
        else:
            print(f"DEBUG: File base_tool.py has fewer than {start_line+1} lines.")
        print("-" * 30)
except Exception as debug_e:
    print(f"DEBUG: Error during pre-import file read: {debug_e}")
# --- END TEMPORARY DEBUGGING ---


# Configure logging
logging.basicConfig(
    level=logging.INFO, # Set to DEBUG for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Log to standard output
        # Optionally add FileHandler here if needed
        # logging.FileHandler("cpas3_app.log")
    ]
)

# --- Attempt to import core components ---
try:
    # These should be absolute imports from the project perspective
    from modules.agents.agent_manager import AgentManager
    # Import other core components if they are directly used in main
    # from modules.memory.structured_memory import StructuredMemory # If needed directly
    # from modules.tools.tool_manager import ToolManager # If needed directly
    logger = logging.getLogger(__name__) # Get logger after basicConfig
except ImportError as e:
    # Log error if initial imports fail
    initial_logger = logging.getLogger(__name__)
    initial_logger.error(f"Failed to import core modules: {e}. Is PYTHONPATH set correctly or are you running from the project root?", exc_info=True)
    sys.exit(1) # Exit if core components cannot be imported
except Exception as e:
    initial_logger = logging.getLogger(__name__)
    initial_logger.error(f"An unexpected error occurred during initial imports: {e}", exc_info=True)
    sys.exit(1)


# --- Global variables for signal handling ---
shutdown_requested = False
# Type hint uses Optional which is now imported at the top
agent_manager_instance: Optional[AgentManager] = None # Hold the manager instance

def handle_signal(signum, frame):
    """Signal handler for graceful shutdown."""
    global shutdown_requested
    if not shutdown_requested:
        logger.info(f"Shutdown signal received (Signal {signum}). Initiating graceful shutdown...")
        shutdown_requested = True
    else:
         logger.warning("Shutdown already in progress. Please wait.")


def main():
    """Main application entry point."""
    global agent_manager_instance # Allow modification of the global instance

    logger.info("Starting CPAS3...")

    # --- Initialize Agent Manager (which initializes Memory and ToolManager) ---
    try:
        # Use environment variables or config files for paths in a real app
        agent_state_dir = os.environ.get("CPAS_AGENT_STATE_DIR") # Example using env var
        memory_db_path = os.environ.get("CPAS_MEMORY_DB_PATH") # Example using env var

        # Use defaults if environment variables aren't set
        if not agent_state_dir:
             agent_state_dir = os.path.join(os.path.expanduser("~"), ".cpas3", "agents")
             logger.info(f"CPAS_AGENT_STATE_DIR not set, using default: {agent_state_dir}")
        else:
             logger.info(f"Using agent state directory from env var: {agent_state_dir}")

        if not memory_db_path:
             memory_db_path = os.path.join(os.path.expanduser("~"), ".cpas3", "cpas_memory.db")
             logger.info(f"CPAS_MEMORY_DB_PATH not set, using default: {memory_db_path}")
        else:
             logger.info(f"Using memory database path from env var: {memory_db_path}")


        agent_manager_instance = AgentManager(
            agent_state_dir=agent_state_dir,
            memory_db_path=memory_db_path
        )
        logger.info("AgentManager initialized successfully.")

        # Check if critical components failed to initialize within AgentManager
        if not agent_manager_instance or not agent_manager_instance.memory:
             logger.critical("Structured Memory failed to initialize within AgentManager. Cannot continue.")
             sys.exit(1)
        if not agent_manager_instance or not agent_manager_instance.tool_manager:
             logger.critical("Tool Manager failed to initialize within AgentManager. Cannot continue.")
             sys.exit(1)

    except Exception as e:
        logger.critical(f"Failed to initialize AgentManager: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Core components initialized. Application logic would start here.")

    # --- Example Application Logic ---
    # Check if any agents were loaded
    if not agent_manager_instance.agents:
        logger.info("No active agents found or loaded. Creating a placeholder 'DemoAgent'.")
        demo_agent = agent_manager_instance.create_agent(
            agent_type="DemoAgent",
            config={"mode": "demonstration", "initial_prompt": "Perform a test calculation."}
        )
        if demo_agent:
            logger.info(f"Created demo agent with ID: {demo_agent.agent_id}")
            agent_to_run = demo_agent
        else:
            logger.error("Failed to create the demo agent.")
            agent_to_run = None
    else:
        # If agents were loaded, maybe pick the first one? Or implement logic to select/activate.
        first_agent_id = list(agent_manager_instance.agents.keys())[0]
        logger.info(f"Using first loaded agent for demo run: {first_agent_id}")
        agent_to_run = agent_manager_instance.get_agent(first_agent_id)


    # Run the selected agent if it exists
    if agent_to_run:
        logger.info(f"Running agent: {agent_to_run.agent_id}")
        # --- Pass inputs to trigger calculator ---
        run_output = agent_to_run.run(inputs={'task': 'calculate', 'op': 'multiply', 'a': 7, 'b': 6})
        logger.info(f"Agent run output: {run_output}")
    else:
         logger.warning("No agent available to run.")


    # --- Main application loop (placeholder) ---
    logger.info("Application running (no UI mode). Press Ctrl+C to exit.")
    while not shutdown_requested:
        try:
            # In a real application, this loop would handle:
            # - Waiting for user input (CLI or UI)
            # - Receiving external triggers (API calls, scheduled events)
            # - Checking agent statuses and deciding which agent(s) to run next
            # - Processing outputs from agent runs
            time.sleep(1) # Keep the main thread alive
        except KeyboardInterrupt:
            # This is handled by the signal handler now, but keep loop structure
            logger.info("KeyboardInterrupt caught in loop (should be handled by signal).")
            break # Exit loop if signal handler didn't set flag correctly
        except Exception as e:
             logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
             # Decide if the error is fatal or recoverable
             # Maybe add a delay before continuing?
             time.sleep(5)


    # --- Graceful Shutdown ---
    logger.info("Shutdown initiated outside main loop...")
    if agent_manager_instance:
        logger.info("Calling AgentManager shutdown...")
        agent_manager_instance.shutdown()
    else:
        logger.info("AgentManager instance not available for shutdown.")

    logger.info("CPAS3 shutdown complete.")


if __name__ == "__main__":
    # --- Register signal handlers ---
    signal.signal(signal.SIGINT, handle_signal)  # Handle Ctrl+C
    signal.signal(signal.SIGTERM, handle_signal) # Handle termination signals

    main() # Run the main application logic

