import json
import os
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Define the default configuration structure
DEFAULT_CONFIG = {
    "llm_provider": "ollama",  # e.g., "ollama", "openai"
    "llm_model": "mistral:7b", # Specific model name
    "llm_base_url": "http://localhost:11434", # Base URL for Ollama or similar
    "llm_api_key": None, # Placeholder for API keys (e.g., OpenAI)
    "max_history_length": 50, # Max entries per agent history
    "agent_defaults": {
        "max_iterations": 15,
        "temperature": 0.7,
        "default_prompt": "You are a helpful assistant."
    },
    "resource_monitor_interval": 5, # Seconds
    # Add other configuration keys as needed
}

class ConfigManager:
    """Manages loading and accessing application configuration."""

    def __init__(self, config_dir: Optional[str] = None, config_file_name: str = "config.json"):
        """
        Initializes the ConfigManager.

        Args:
            config_dir: The directory to store/load the config file. Defaults to ~/.cpas3.
            config_file_name: The name of the configuration file.
        """
        if config_dir is None:
            self.config_dir = os.path.join(os.path.expanduser("~"), ".cpas3")
        else:
            self.config_dir = config_dir

        self.config_file_path = os.path.join(self.config_dir, config_file_name)
        self.config_data = {}
        self._load_config()

    def _ensure_config_dir_exists(self):
        """Creates the configuration directory if it doesn't exist."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            logger.debug(f"Configuration directory ensured: {self.config_dir}")
        except OSError as e:
            logger.error(f"Failed to create configuration directory {self.config_dir}: {e}", exc_info=True)
            raise # Re-raise the exception as this is critical

    def _load_config(self):
        """Loads configuration from the file, creating it with defaults if it doesn't exist."""
        self._ensure_config_dir_exists()
        try:
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, 'r') as f:
                    loaded_data = json.load(f)
                    # Merge loaded data with defaults to ensure all keys exist
                    self.config_data = {**DEFAULT_CONFIG, **loaded_data}
                    logger.info(f"Loaded configuration from {self.config_file_path}")
                    # Optionally: Check for missing keys compared to DEFAULT_CONFIG and add them
                    self._update_config_with_defaults()

            else:
                logger.warning(f"Configuration file not found at {self.config_file_path}. Creating with defaults.")
                self.config_data = DEFAULT_CONFIG.copy()
                self.save_config() # Save the default config immediately

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.config_file_path}: {e}. Using default config.", exc_info=True)
            self.config_data = DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}. Using default config.", exc_info=True)
            self.config_data = DEFAULT_CONFIG.copy()

    def _update_config_with_defaults(self):
        """Adds missing default keys to the loaded config."""
        updated = False
        for key, value in DEFAULT_CONFIG.items():
            if key not in self.config_data:
                self.config_data[key] = value
                updated = True
                logger.info(f"Added missing default config key: '{key}'")
        if updated:
            self.save_config() # Save if defaults were added

    def save_config(self):
        """Saves the current configuration data to the file."""
        self._ensure_config_dir_exists()
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(self.config_data, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {self.config_file_path}: {e}", exc_info=True)

    # *** ADDED GET METHOD ***
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value by key.

        Args:
            key: The configuration key to retrieve.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value or the default value.
        """
        return self.config_data.get(key, default)

    # Optional: Method to set a value and save
    def set(self, key: str, value: Any):
        """
        Sets a configuration value and saves the config file.

        Args:
            key: The configuration key to set.
            value: The value to set for the key.
        """
        self.config_data[key] = value
        self.save_config()
        logger.info(f"Configuration key '{key}' set and config saved.")

    # Optional: Allow dictionary-like access
    def __getitem__(self, key: str) -> Any:
        """Allows dictionary-like access (e.g., config['llm_provider'])."""
        # Return None or raise KeyError if key not found? Let's return None.
        return self.config_data.get(key)

    def __setitem__(self, key: str, value: Any):
        """Allows dictionary-like setting (e.g., config['llm_provider'] = 'new')."""
        self.set(key, value)

