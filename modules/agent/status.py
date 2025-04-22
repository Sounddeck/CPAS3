# filepath: modules/agent/status.py
from enum import Enum

class AgentStatus(Enum):
    """Represents the possible states of an agent."""
    UNKNOWN = "unknown"
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting" # Added for clarity during init/thread start
