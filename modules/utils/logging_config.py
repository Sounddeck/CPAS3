import os
import logging
import logging.config
import json
from typing import Dict, Any, Optional # <-- Import moved to the top

DEFAULT_LOGGING_CONFIG_FILENAME = "logging_config.json"
DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(funcName)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO", # Console level
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "level": "DEBUG", # File level
            "filename": "cpas3.log", # Placeholder, will be updated
            "maxBytes": 10485760, # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        },
    },
    "loggers": {
        "": { # Root logger
            "handlers": ["console", "file"],
            "level": "DEBUG", # Lowest level to capture everything
            "propagate": False, # Prevent root logger messages from propagating further if needed
        },
        "urllib3": { # Example: Reduce noise from http libraries
             "handlers": ["file"], # Send only to file, not console
             "level": "WARNING",
             "propagate": False,
        },
         "httpx": { # Example: Reduce noise from http libraries
              "handlers": ["file"],
              "level": "WARNING",
              "propagate": False,
         },
         "langsmith": { # Example: Reduce noise from langsmith
              "handlers": ["file"],
              "level": "INFO",
              "propagate": False,
         }
        # Add specific logger configurations here if needed
        # "modules.agent": {
        #     "handlers": ["console", "file"],
        #     "level": "DEBUG",
        #     "propagate": False,
        # },
    }
}

def setup_logging(
    config_dir: str,
    config_filename: str = DEFAULT_LOGGING_CONFIG_FILENAME,
    default_config: Dict[str, Any] = DEFAULT_LOGGING_CONFIG,
    log_level_override: Optional[str] = None # Allow overriding root level via code
) -> None:
    """
    Sets up logging configuration for the application.

    Loads configuration from a JSON file within the config_dir.
    If the file doesn't exist, it creates one with default settings.

    Args:
        config_dir: The directory containing configuration files.
        config_filename: The name of the logging configuration file.
        default_config: The default logging configuration dictionary.
        log_level_override: Optional log level (e.g., "DEBUG", "INFO") to force set on the root logger.
    """
    config_filepath = os.path.join(config_dir, config_filename)
    log_file_path = os.path.join(config_dir, default_config['handlers']['file']['filename']) # Default log file path

    loaded_config = default_config # Start with defaults

    if os.path.exists(config_filepath):
        try:
            with open(config_filepath, 'rt') as f:
                loaded_config = json.load(f)
            print(f"Logging configuration loaded from: {config_filepath}") # Use print before logging is fully configured
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading logging config from {config_filepath}: {e}. Using default config.")
            loaded_config = default_config
            # Attempt to save defaults if loading failed
            try:
                 with open(config_filepath, 'wt') as f:
                      json.dump(loaded_config, f, indent=4)
                 print(f"Default logging configuration saved to: {config_filepath}")
            except IOError as save_error:
                 print(f"Error saving default logging config to {config_filepath}: {save_error}")

    else:
        print(f"Logging configuration file not found at {config_filepath}. Creating with default settings.")
        loaded_config = default_config
        try:
            # Ensure the directory exists before writing
            os.makedirs(config_dir, exist_ok=True)
            with open(config_filepath, 'wt') as f:
                json.dump(loaded_config, f, indent=4)
            print(f"Default logging configuration saved to: {config_filepath}")
        except IOError as e:
            print(f"Error saving default logging config to {config_filepath}: {e}")

    # --- Configure File Handler Path ---
    # Update the filename in the config dictionary *before* configuring logging
    if 'handlers' in loaded_config and 'file' in loaded_config['handlers']:
        # Use the log file name defined in the config, placed in the config_dir
        config_log_filename = loaded_config['handlers']['file'].get('filename', 'cpas3.log')
        log_file_path = os.path.join(config_dir, config_log_filename)
        loaded_config['handlers']['file']['filename'] = log_file_path
        print(f"Log file path set to: {log_file_path}")
    else:
         print(f"Warning: 'file' handler configuration not found or incomplete. Using default path: {log_file_path}")
         # Ensure default path is used if config structure is broken
         if 'handlers' in loaded_config and 'file' in loaded_config['handlers']:
              loaded_config['handlers']['file']['filename'] = log_file_path

    # --- Apply Log Level Override ---
    if log_level_override:
        log_level_override = log_level_override.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level_override in valid_levels:
             if "" in loaded_config.get("loggers", {}):
                  loaded_config["loggers"][""]["level"] = log_level_override
                  print(f"Root logger level overridden to: {log_level_override}")
             if "root" in loaded_config: # Handle older 'root' key style too
                  loaded_config["root"]["level"] = log_level_override
                  print(f"Root logger level overridden to: {log_level_override}")
        else:
             print(f"Warning: Invalid log_level_override '{log_level_override}'. Using level from config.")


    # --- Apply Logging Configuration ---
    try:
        logging.config.dictConfig(loaded_config)
        # Get the root logger after configuration
        root_logger = logging.getLogger()
        print(f"Logging configured successfully. Root logger level: {logging.getLevelName(root_logger.level)}")
    except (ValueError, TypeError, AttributeError, ImportError) as e:
        print(f"Error applying logging dictionary configuration: {e}")
        # Fallback to basic config if dictConfig fails
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        logging.error("Fell back to basic logging configuration due to an error.")

# No need for the import at the end anymore
