import os
import json
import logging
from typing import Dict, Optional, List, Any
import datetime

# Assuming AgentState and HistoryEntry models are defined elsewhere and importable if needed directly
# from ..models import AgentState, HistoryEntry # Adjust import path as necessary

logger = logging.getLogger(__name__)

MANIFEST_FILE = "agent_manifest.json"
HISTORY_SUFFIX = ".history.jsonl"
STATE_SUFFIX = ".state.json"

class AgentStore:
    """Handles persistence of agent states and history to the file system."""

    def __init__(self, data_dir: str):
        """
        Initializes the AgentStore.

        Args:
            data_dir: The directory where agent data (manifest, states, history) will be stored.
        """
        self.data_dir = data_dir
        self.manifest_path = os.path.join(self.data_dir, MANIFEST_FILE)
        self._ensure_data_dir_exists()
        logger.info(f"AgentStore initialized. Data directory: {self.data_dir}")

    def _ensure_data_dir_exists(self):
        """Creates the data directory if it doesn't exist."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create data directory {self.data_dir}: {e}", exc_info=True)
            raise # Critical error if we can't create the data directory

    # --- Manifest Management ---

    def _load_manifest(self) -> Dict[str, str]:
        """Loads the agent manifest (agent_id -> agent_name)."""
        if not os.path.exists(self.manifest_path):
            return {}
        try:
            with open(self.manifest_path, 'r') as f:
                manifest_data = json.load(f)
                if not isinstance(manifest_data, dict):
                     logger.warning(f"Manifest file {self.manifest_path} does not contain a dictionary. Returning empty manifest.")
                     return {}
                return manifest_data
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from manifest file {self.manifest_path}. Returning empty manifest.", exc_info=True)
            return {}
        except Exception as e:
            logger.error(f"Failed to load manifest file {self.manifest_path}: {e}. Returning empty manifest.", exc_info=True)
            return {}

    def _save_manifest(self, manifest_data: Dict[str, str]):
        """Saves the agent manifest."""
        try:
            with open(self.manifest_path, 'w') as f:
                json.dump(manifest_data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save manifest file {self.manifest_path}: {e}", exc_info=True)

    def add_agent_to_manifest(self, agent_id: str, agent_name: str):
        """Adds an agent's ID and name to the manifest."""
        manifest = self._load_manifest()
        if agent_id not in manifest:
            manifest[agent_id] = agent_name
            self._save_manifest(manifest)
            logger.info(f"Agent {agent_id[:8]} ('{agent_name}') added to manifest.")
        else:
             # Optionally update name if it changed?
             if manifest[agent_id] != agent_name:
                  logger.warning(f"Agent {agent_id[:8]} already in manifest with name '{manifest[agent_id]}'. Updating name to '{agent_name}'.")
                  manifest[agent_id] = agent_name
                  self._save_manifest(manifest)


    def remove_agent_from_manifest(self, agent_id: str):
        """Removes an agent from the manifest."""
        manifest = self._load_manifest()
        if agent_id in manifest:
            del manifest[agent_id]
            self._save_manifest(manifest)
            logger.info(f"Agent {agent_id[:8]} removed from manifest.")

    def get_agent_name(self, agent_id: str) -> Optional[str]:
        """Gets an agent's name from the manifest."""
        manifest = self._load_manifest()
        return manifest.get(agent_id)

    def get_all_agent_ids(self) -> List[str]:
         """Gets a list of all agent IDs from the manifest."""
         manifest = self._load_manifest()
         return list(manifest.keys())

    # --- Agent State Management ---

    def _get_state_file_path(self, agent_id: str) -> str:
        """Constructs the file path for an agent's state file."""
        return os.path.join(self.data_dir, f"{agent_id}{STATE_SUFFIX}")

    def save_agent_state(self, agent_id: str, state_data: Any): # Accept AgentState or dict
        """
        Saves an agent's state to a JSON file.

        Args:
            agent_id: The ID of the agent.
            state_data: The agent's state (should be AgentState object or dict).
        """
        state_file_path = self._get_state_file_path(agent_id)
        try:
            # *** CONVERT AgentState TO DICT BEFORE SAVING ***
            data_to_save = state_data
            if hasattr(state_data, 'to_dict') and callable(state_data.to_dict):
                 data_to_save = state_data.to_dict()
            elif not isinstance(state_data, dict):
                 logger.error(f"Cannot save state for agent {agent_id[:8]}: state_data is not a dict and has no to_dict() method.")
                 return # Or raise error

            with open(state_file_path, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            # logger.debug(f"Saved state for agent {agent_id[:8]} to {os.path.basename(state_file_path)}")
        except Exception as e:
            logger.error(f"Error saving state for agent {agent_id[:8]} to {os.path.basename(state_file_path)}: {e}", exc_info=True)

    def load_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads an agent's state from its JSON file.

        Args:
            agent_id: The ID of the agent.

        Returns:
            A dictionary representing the agent's state, or None if not found or error occurs.
        """
        state_file_path = self._get_state_file_path(agent_id)
        if not os.path.exists(state_file_path):
            logger.warning(f"State file not found for agent {agent_id[:8]} at {os.path.basename(state_file_path)}")
            return None
        try:
            with open(state_file_path, 'r') as f:
                state_data = json.load(f)
                # Basic validation: ensure it's a dictionary
                if not isinstance(state_data, dict):
                    logger.error(f"State file {os.path.basename(state_file_path)} for agent {agent_id[:8]} does not contain a valid JSON object (dictionary).")
                    return None
                # Add agent_id if it's missing (older format?)
                if 'agent_id' not in state_data:
                     state_data['agent_id'] = agent_id
                return state_data
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from state file {os.path.basename(state_file_path)} for agent {agent_id[:8]}.", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Failed to load state file {os.path.basename(state_file_path)} for agent {agent_id[:8]}: {e}", exc_info=True)
            return None

    def remove_agent_state(self, agent_id: str):
        """Removes an agent's state file."""
        state_file_path = self._get_state_file_path(agent_id)
        if os.path.exists(state_file_path):
            try:
                os.remove(state_file_path)
                logger.info(f"Removed state file for agent {agent_id[:8]}.")
            except OSError as e:
                logger.error(f"Failed to remove state file {os.path.basename(state_file_path)} for agent {agent_id[:8]}: {e}", exc_info=True)

    def get_all_agent_states(self) -> Dict[str, Optional[Dict[str, Any]]]:
         """Loads states for all agents listed in the manifest."""
         all_states = {}
         agent_ids = self.get_all_agent_ids()
         for agent_id in agent_ids:
              state = self.load_agent_state(agent_id)
              # We store None if loading fails to indicate an issue
              all_states[agent_id] = state
         return all_states


    # --- Agent History Management (JSON Lines format) ---

    def _get_history_file_path(self, agent_id: str) -> str:
        """Constructs the file path for an agent's history file."""
        return os.path.join(self.data_dir, f"{agent_id}{HISTORY_SUFFIX}")

    def save_agent_history(self, agent_id: str, history_entries: List[Dict[str, Any]]):
        """
        Saves agent history entries to a JSON Lines file (overwrites existing file).

        Args:
            agent_id: The ID of the agent.
            history_entries: A list of dictionaries, each representing a history entry.
        """
        history_file_path = self._get_history_file_path(agent_id)
        try:
            with open(history_file_path, 'w') as f:
                for entry in history_entries:
                    # Ensure entry is a dict before dumping
                    if isinstance(entry, dict):
                         json.dump(entry, f)
                         f.write('\n')
                    else:
                         logger.warning(f"Skipping non-dict history entry for agent {agent_id[:8]}: {type(entry)}")
            # logger.debug(f"Saved history for agent {agent_id[:8]} to {os.path.basename(history_file_path)}")
        except Exception as e:
            logger.error(f"Error saving history for agent {agent_id[:8]} to {os.path.basename(history_file_path)}: {e}", exc_info=True)

    def append_history_entry(self, agent_id: str, history_entry: Dict[str, Any]):
         """Appends a single history entry to the agent's history file."""
         history_file_path = self._get_history_file_path(agent_id)
         if not isinstance(history_entry, dict):
              logger.error(f"Cannot append history entry for agent {agent_id[:8]}: entry is not a dictionary.")
              return
         try:
              with open(history_file_path, 'a') as f:
                   json.dump(history_entry, f)
                   f.write('\n')
              # logger.debug(f"Appended history entry for agent {agent_id[:8]}.")
         except Exception as e:
              logger.error(f"Error appending history entry for agent {agent_id[:8]} to {os.path.basename(history_file_path)}: {e}", exc_info=True)


    def load_agent_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Loads agent history from its JSON Lines file.

        Args:
            agent_id: The ID of the agent.

        Returns:
            A list of dictionaries representing the history entries, or an empty list if not found/error.
        """
        history_file_path = self._get_history_file_path(agent_id)
        if not os.path.exists(history_file_path):
            return []
        history = []
        try:
            with open(history_file_path, 'r') as f:
                for line in f:
                    if line.strip(): # Avoid empty lines
                        try:
                            entry = json.loads(line)
                            if isinstance(entry, dict):
                                 history.append(entry)
                            else:
                                 logger.warning(f"Skipping non-dict entry in history file {os.path.basename(history_file_path)} for agent {agent_id[:8]}: {line.strip()}")
                        except json.JSONDecodeError:
                            logger.error(f"Error decoding JSON line in history file {os.path.basename(history_file_path)} for agent {agent_id[:8]}: {line.strip()}", exc_info=True)
            return history
        except Exception as e:
            logger.error(f"Failed to load history file {os.path.basename(history_file_path)} for agent {agent_id[:8]}: {e}", exc_info=True)
            return []

    def remove_agent_history(self, agent_id: str):
        """Removes an agent's history file."""
        history_file_path = self._get_history_file_path(agent_id)
        if os.path.exists(history_file_path):
            try:
                os.remove(history_file_path)
                logger.info(f"Removed history file for agent {agent_id[:8]}.")
            except OSError as e:
                logger.error(f"Failed to remove history file {os.path.basename(history_file_path)} for agent {agent_id[:8]}: {e}", exc_info=True)
