# --- Start copying here ---
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Any, List, Optional

# Import AgentStatus and AgentTask if needed for type hinting in signals
# Adjust path based on actual location if needed
try:
    from ..agent.models import AgentStatus, AgentTask
except ImportError:
    # Define dummy types if models aren't available during UI-only work
    # This might happen if you're designing the UI separately
    logging.warning("Could not import agent models for signal type hinting. Using Any.")
    AgentStatus = Any
    AgentTask = Any


logger = logging.getLogger(__name__)

class SignalEmitter(QObject):
    """
    A central emitter for signals connecting the backend (AgentManager, etc.)
    to the UI (MainWindow, etc.). Uses PyQt signals.
    """
    # Agent signals
    agent_created = pyqtSignal(dict)         # Emits agent state dict
    agent_removed = pyqtSignal(str)          # Emits agent_id
    agent_status_updated = pyqtSignal(str, AgentStatus) # Emits agent_id, new_status (enum)
    agent_task_updated = pyqtSignal(str, dict) # Emits agent_id, task state dict or empty dict if cleared
    agent_history_updated = pyqtSignal(str, dict) # Emits agent_id, history entry dict

    # Task signals
    task_created = pyqtSignal(dict)          # Emits task state dict
    task_queue_updated = pyqtSignal(list)    # Emits list of task state dicts in queue

    # Monitoring signals
    resource_usage_updated = pyqtSignal(dict) # Emits dict with 'cpu', 'memory' usage

    # General application signals (add more as needed)
    log_message = pyqtSignal(str, str)      # Emits log level (str), message (str)
    error_occurred = pyqtSignal(str, str)   # Emits error type/location, message

    def __init__(self):
        super().__init__()
        logger.debug("SignalEmitter initialized.")

# --- Global Instance ---
# Create a single, globally accessible instance of the emitter
signal_emitter = SignalEmitter()
logger.info("Global signal_emitter instance created.")
# ---
# --- Stop copying here ---
