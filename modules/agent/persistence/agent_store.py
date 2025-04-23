import os
import json
import logging
import threading
from typing import Dict, Any, Optional, List

# Assuming BaseAgent structure defines get_serializable_config and get_serializable_state
# If not, imports might need adjustment or base class needs defining first.
# We don't actually import BaseAgent here to avoid circular dependencies if AgentManager uses AgentStore.
# We rely on the dictionary structures provided by the agents.

logger = logging.getLogger(__name__)

class AgentStore:
    """
    Handles persistence (saving and loading) of agent configurations and states.
    Currently saves to JSON files in a specified directory.
    """
    def __init__(self, storage_path: str = "data/agents"):
        self.storage_path = storage_path
        self._ensure_storage_path_exists()
        self._lock = threading.Lock() # Lock for thread-safe file operations
        logger.info(f"AgentStore initialized. Storage path: '{self.storage_path}'")

    def _ensure_storage_path_exists(self):
        """Creates the storage directory if it doesn't exist."""
        try:
            os.makedirs(self.storage_path, exist_ok=True)
            logger.debug(f"Storage path '{self.storage_path}' ensured.")
        except OSError as e:
            logger.error(f"Failed to create agent storage directory '{self.storage_path}': {e}", exc_info=True)
            raise # Re-raise the error as this is critical

    def _get_agent_filepath(self, agent_id: str) -> str:
        """Constructs the full filepath for an agent's data file."""
        # Basic sanitization: remove path separators from agent_id to prevent traversal
        safe_agent_id = agent_id.replace(os.path.sep, "_").replace("..", "_")
        if not safe_agent_id:
            raise ValueError("Agent ID cannot be empty or consist only of path separators.")
        return os.path.join(self.storage_path, f"{safe_agent_id}.json")

    def save_agent(self, agent_config: Dict[str, Any], agent_state: Dict[str, Any]):
        """
        Saves the configuration and current state of an agent.
        Overwrites the existing file for the agent if it exists.

        Args:
            agent_config: Dictionary containing the agent's static configuration
                          (e.g., name, type, LLM config, tools list). Should include 'agent_id'.
            agent_state: Dictionary containing the agent's dynamic state
                         (e.g., status, current task, simple memory state). Should include 'agent_id'.
        """
        agent_id = agent_config.get('agent_id')
        if not agent_id:
            logger.error("Cannot save agent: 'agent_id' missing from configuration.")
            return
        if agent_state.get('agent_id') != agent_id:
             logger.error(f"Agent ID mismatch between config ('{agent_id}') and state ('{agent_state.get('agent_id')}'). Cannot save.")
             return

        filepath = self._get_agent_filepath(agent_id)
        data_to_save = {
            "config": agent_config,
            "state": agent_state
        }

        with self._lock: # Ensure thread safety during file write
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=4, ensure_ascii=False)
                logger.info(f"Agent '{agent_config.get('name', agent_id)}' (ID: {agent_id[:8]}) saved to '{filepath}'")
            except (IOError, TypeError, ValueError) as e:
                logger.error(f"Failed to save agent {agent_id[:8]} to '{filepath}': {e}", exc_info=True)
            except Exception as e:
                 logger.error(f"An unexpected error occurred while saving agent {agent_id[:8]}: {e}", exc_info=True)


    def load_agent_data(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads the configuration and state for a specific agent ID.

        Args:
            agent_id: The unique identifier of the agent to load.

        Returns:
            A dictionary containing 'config' and 'state' keys if found, otherwise None.
        """
        filepath = self._get_agent_filepath(agent_id)
        if not os.path.exists(filepath):
            logger.debug(f"Agent data file not found for ID {agent_id[:8]} at '{filepath}'.")
            return None

        with self._lock: # Ensure thread safety during file read
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Basic validation
                if 'config' in data and 'state' in data and data['config'].get('agent_id') == agent_id:
                    logger.info(f"Agent '{data['config'].get('name', agent_id)}' (ID: {agent_id[:8]}) loaded from '{filepath}'")
                    return data
                else:
                    logger.warning(f"Invalid or incomplete data found for agent {agent_id[:8]} in '{filepath}'. Skipping load.")
                    return None
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load or parse agent data for {agent_id[:8]} from '{filepath}': {e}", exc_info=True)
                return None
            except Exception as e:
                 logger.error(f"An unexpected error occurred while loading agent {agent_id[:8]}: {e}", exc_info=True)
                 return None

    def load_all_agent_data(self) -> List[Dict[str, Any]]:
        """Loads data for all agents found in the storage directory."""
        all_agent_data = []
        logger.info(f"Loading all agents from '{self.storage_path}'...")
        try:
            # List only .json files to avoid loading other potential files/dirs
            agent_files = [f for f in os.listdir(self.storage_path)
                           if os.path.isfile(os.path.join(self.storage_path, f)) and f.endswith('.json')]
        except FileNotFoundError:
            logger.warning(f"Agent storage directory '{self.storage_path}' not found during load_all. Returning empty list.")
            return []
        except OSError as e:
            logger.error(f"Error listing agent files in '{self.storage_path}': {e}", exc_info=True)
            return []


        for filename in agent_files:
            agent_id = filename[:-5] # Remove '.json' extension
            agent_data = self.load_agent_data(agent_id) # Use existing load method (handles locking)
            if agent_data:
                all_agent_data.append(agent_data)

        logger.info(f"Loaded data for {len(all_agent_data)} agents.")
        return all_agent_data

    def delete_agent(self, agent_id: str) -> bool:
        """
        Deletes the data file associated with an agent ID.

        Args:
            agent_id: The unique identifier of the agent to delete.

        Returns:
            True if the file was successfully deleted, False otherwise.
        """
        filepath = self._get_agent_filepath(agent_id)
        if not os.path.exists(filepath):
            logger.warning(f"Cannot delete agent {agent_id[:8]}: File not found at '{filepath}'.")
            return False

        with self._lock: # Ensure thread safety during file deletion
            try:
                os.remove(filepath)
                logger.info(f"Agent data for ID {agent_id[:8]} deleted from '{filepath}'.")
                return True
            except OSError as e:
                logger.error(f"Failed to delete agent data file '{filepath}': {e}", exc_info=True)
                return False
            except Exception as e:
                 logger.error(f"An unexpected error occurred while deleting agent {agent_id[:8]}: {e}", exc_info=True)
                 return False

