import os
import logging
from dotenv import load_dotenv

class Config:
    """Loads configuration from .env file and environment variables."""

    def __init__(self):
        load_dotenv() # Load environment variables from .env file

        # --- General Settings ---
        self.app_name = os.getenv("APP_NAME", "CPAS3")
        self.environment = os.getenv("ENVIRONMENT", "development")

        # --- Data Directory (Define BEFORE log dir) ---
        # Default to ~/.cpas3 in the user's home directory
        self._default_data_dir = os.path.join(os.path.expanduser("~"), f".{self.app_name.lower()}")
        self._data_dir = os.getenv("DATA_DIR", self._default_data_dir)
        # Ensure data directory exists early, as log dir depends on it
        self._ensure_dir_exists(self._data_dir)

        # --- Logging (Define AFTER data dir) ---
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.log_date_format = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
        # Now self.get_data_dir() can safely access self._data_dir
        self._log_dir = os.getenv("LOG_DIR", os.path.join(self.get_data_dir(), "logs"))
        self._log_file = os.path.join(self._log_dir, f"{self.app_name.lower()}.log")
        # Ensure log directory exists
        self._ensure_dir_exists(self._log_dir)

        # --- Agent Settings ---
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.default_agent_model = os.getenv("DEFAULT_AGENT_MODEL", "llama3")
        self.file_tool_base_dir = os.getenv("FILE_TOOL_BASE_DIR", None) # Or set a default path string

        # --- LangSmith Tracing (Optional) ---
        self.langsmith_tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.langsmith_api_key = os.getenv("LANGCHAIN_API_KEY", None) # Optional, can be set in env directly
        self.langsmith_project = os.getenv("LANGCHAIN_PROJECT", f"{self.app_name}-{self.environment}") # Example project name

        # Validation can happen after all attributes are initially set
        self._validate_config()

    def _ensure_dir_exists(self, dir_path):
        """Creates a directory if it doesn't exist."""
        if dir_path and not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
                # Use basic print here as logging might not be fully configured yet during init
                print(f"INFO: Created directory: {dir_path}")
            except OSError as e:
                print(f"ERROR: Error creating directory {dir_path}: {e}")
                # Decide if this is fatal. For now, we print and continue.

    def _validate_config(self):
        """Validates configuration values."""
        # Example validation: Check log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            print(f"WARNING: Invalid LOG_LEVEL '{self.log_level}'. Defaulting to INFO.")
            self.log_level = "INFO"
        # Add more validations as needed

    def get_data_dir(self) -> str:
        """Returns the base data directory path."""
        # This check ensures it doesn't fail if called before _data_dir is set,
        # although the reordering should prevent that now.
        if not hasattr(self, '_data_dir'):
             raise AttributeError("'_data_dir' accessed before initialization in Config.")
        return self._data_dir

    def get_log_file_path(self) -> str:
        """Returns the full path to the log file."""
        if not hasattr(self, '_log_file'):
             raise AttributeError("'_log_file' accessed before initialization in Config.")
        return self._log_file

    def __repr__(self):
        # Represent the config, hiding sensitive info if necessary
        # Safely access attributes that might not be set if init failed early
        data_dir = getattr(self, '_data_dir', 'N/A')
        log_level = getattr(self, 'log_level', 'N/A')
        tracing = getattr(self, 'langsmith_tracing_enabled', False)
        return (f"Config(app_name='{self.app_name}', environment='{self.environment}', "
                f"log_level='{log_level}', data_dir='{data_dir}', "
                f"langsmith_tracing={'enabled' if tracing else 'disabled'})")

# Example usage (optional, for testing)
if __name__ == "__main__":
    # Use basic print for testing __main__ block as logging depends on Config
    try:
        config = Config()
        print(config)
        print(f"Log file path: {config.get_log_file_path()}")
        print(f"Data directory: {config.get_data_dir()}")
        print(f"File Tool Base Dir: {config.file_tool_base_dir}")
    except Exception as e:
        print(f"Error during Config test: {e}")


