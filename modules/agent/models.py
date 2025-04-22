import uuid
import logging
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
import datetime

logger = logging.getLogger(__name__)

# --- Agent Status Enum ---
class AgentStatus(Enum):
    """Enumeration for agent states."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping" # <-- ADDED
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"

# --- Agent Configuration Model ---
class AgentConfig(BaseModel):
    """Configuration settings for an agent instance."""
    max_iterations: int = Field(default=15, description="Maximum iterations for the agent loop.")
    temperature: float = Field(default=0.7, description="LLM temperature for generation.")
    verbose: bool = Field(default=True, description="Enable verbose logging for agent execution.")
    handle_parsing_errors: bool = Field(default=True, description="Attempt to handle LLM output parsing errors.")
    early_stopping_method: str = Field(default="generate", description="Method for early stopping if needed.")
    auto_start: bool = Field(default=True, description="Whether the agent should start its loop automatically.")
    default_prompt: Optional[str] = Field(default="You are a helpful assistant.", description="Default system prompt.")

    class Config:
        use_enum_values = True

# --- Agent Task Model ---
class AgentTask(BaseModel):
    """Represents a task assigned to an agent."""
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: Optional[str] = None
    description: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    result: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        d['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        return d

# --- Agent State Model (for persistence) ---
class AgentState(BaseModel):
    """Represents the serializable state of an agent instance."""
    agent_id: str
    name: str
    status: AgentStatus = AgentStatus.UNKNOWN
    config: AgentConfig
    created_at: Optional[datetime.datetime] = None
    last_updated: Optional[datetime.datetime] = None

    class Config:
        use_enum_values = True

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d['status'] = self.status.value
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        d['last_updated'] = self.last_updated.isoformat() if self.last_updated else None
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        status_str = data.get('status', AgentStatus.UNKNOWN.value)
        try:
            data['status'] = AgentStatus(status_str)
        except ValueError:
            logger.warning(f"Invalid status '{status_str}' found in state data for agent {data.get('agent_id', 'N/A')}. Using UNKNOWN.")
            data['status'] = AgentStatus.UNKNOWN

        if 'config' in data and isinstance(data['config'], dict):
             try:
                 data['config'] = AgentConfig(**data['config'])
             except Exception as e:
                 logger.error(f"Failed to parse 'config' dict into AgentConfig for agent {data.get('agent_id', 'N/A')}: {e}. Using default config.", exc_info=True)
                 data['config'] = AgentConfig()
        elif 'config' not in data:
             logger.warning(f"Missing 'config' in state data for agent {data.get('agent_id', 'N/A')}. Using default config.")
             data['config'] = AgentConfig()

        for key in ['created_at', 'last_updated']:
             if key in data and isinstance(data[key], str):
                  try:
                       data[key] = datetime.datetime.fromisoformat(data[key].replace('Z', '+00:00'))
                  except ValueError:
                       try:
                            data[key] = datetime.datetime.fromisoformat(data[key])
                       except ValueError:
                            logger.warning(f"Could not parse {key} string: {data[key]} for agent {data.get('agent_id', 'N/A')}. Setting to None.")
                            data[key] = None
             elif key in data and data[key] is not None and not isinstance(data[key], datetime.datetime):
                  logger.warning(f"Invalid type for {key} in state data for agent {data.get('agent_id', 'N/A')}: {type(data[key])}. Setting to None.")
                  data[key] = None

        return cls(**data)

# --- History Entry Model ---
class HistoryEntry(BaseModel):
    """Represents a single entry in an agent's history."""
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    entry_type: str
    content: Any
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d['timestamp'] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HistoryEntry':
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            try:
                data['timestamp'] = datetime.datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                 try:
                      data['timestamp'] = datetime.datetime.fromisoformat(data['timestamp'])
                 except ValueError:
                      logger.warning(f"Could not parse timestamp string: {data['timestamp']}. Using current time.")
                      data['timestamp'] = datetime.datetime.utcnow()

        return cls(**data)
