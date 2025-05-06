"""
Configuration loader for CPAS3
Loads settings from .env and environment variables
"""
import os
import logging
from dotenv import load_dotenv

class Config:
    """Loads configuration from .env file and environment variables."""

    def __init__(self):
        load_dotenv()  # Load environment variables from .env file

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
        self.file_tool_base_dir = os.getenv("FILE_TOOL_BASE_DIR", None)  # Or set a default path string

        # --- MongoDB Settings ---
        self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.mongodb_db_name = os.getenv("MONGODB_DB_NAME", "cpas3_memory")
        self.mongodb_langgraph_db = os.getenv("MONGODB_LANGGRAPH_DB", "cpas3_langgraph")

        # --- LangSmith Tracing (Optional) ---
        self.langsmith_tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.langsmith_api_key = os.getenv("LANGCHAIN_API_KEY", None)  # Optional, can be set in env directly
        self.langsmith_project = os.getenv("LANGCHAIN_PROJECT", f"{self.app_name}-{self.environment}")  # Example project name

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
        return self._data_dir

    def get_log_path(self) -> str:
        """Returns the log file path."""
        return self._log_file

    def configure_logging(self):
        """Configure logging based on current settings."""
        log_level = getattr(logging, self.log_level)
        logging.basicConfig(
            level=log_level,
            format=self.log_format,
            datefmt=self.log_date_format,
            handlers=[
                logging.FileHandler(self.get_log_path()),
                logging.StreamHandler()  # Also output to console
            ]
        )
        logging.info(f"Logging configured: level={self.log_level}, file={self.get_log_path()}")
