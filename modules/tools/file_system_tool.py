import os
import logging
from typing import Dict, Any
# --- Removed unused imports ---
# from typing import Type, Optional  # No longer needed with current structure
# from pydantic import BaseModel, Field # Removed
# from langchain_core.tools import BaseTool # Removed

# <<< CORRECTED IMPORT: Ensure only the local BaseTool is imported >>>
from .base_tool import BaseTool

logger = logging.getLogger(__name__)

# Define potential errors for clarity
class FileSystemError(Exception):
    pass
class PathTraversalError(FileSystemError):
    pass
class OperationFailedError(FileSystemError):
    pass

# <<< CORRECTED INHERITANCE: Ensure it inherits from local BaseTool >>>
class FileSystemTool(BaseTool):
    """
    Tool for interacting with a restricted file system workspace.
    Use this tool to list directories, read files, or write files within the designated workspace.
    """
    # --- Required BaseTool Attributes ---
    name: str = "file_system_tool"
    description: str = (
        "Manages files in a restricted workspace. Actions: list_directory, read_file, write_file. "
        "Requires 'action' (string), 'path' (string, relative to workspace), and optionally 'content' (string for write_file)."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The action to perform: list_directory, read_file, or write_file.",
                "enum": ["list_directory", "read_file", "write_file"]
            },
            "path": {
                "type": "string",
                "description": "The relative path within the workspace. Cannot contain '..'."
            },
            "content": {
                "type": "string",
                "description": "The content to write (only used for write_file action)."
            }
        },
        "required": ["action", "path"]
    }

    def __init__(self, root_dir: str):
        """
        Initializes the FileSystemTool.

        Args:
            root_dir (str): The absolute path to the restricted workspace directory.
        """
        if not os.path.isdir(root_dir):
            logger.warning(f"FileSystemTool initialized with non-existent root directory: {root_dir}")
        self.root_dir = os.path.abspath(root_dir)
        logger.info(f"FileSystemTool initialized with root directory: {self.root_dir}")

    def _validate_path(self, path: str) -> str:
        """Validates and resolves the path within the root directory."""
        if not path:
            raise PathTraversalError("Path cannot be empty.")
        if os.path.isabs(path):
             raise PathTraversalError(f"Path '{path}' must be relative, not absolute.")
        if ".." in path.split(os.path.sep):
            raise PathTraversalError("Path cannot contain '..'. Access denied.")

        full_path = os.path.abspath(os.path.join(self.root_dir, path))

        if not full_path.startswith(os.path.abspath(self.root_dir)):
            raise PathTraversalError(f"Path '{path}' resolves outside the allowed workspace ('{self.root_dir}'). Access denied.")

        return full_path

    def execute(self, action: str, path: str, content: str = None) -> Dict[str, Any]:
        """
        Executes the file system action based on the provided arguments.

        Args:
            action (str): The action to perform ('list_directory', 'read_file', 'write_file').
            path (str): The relative path within the workspace.
            content (str, optional): The content for the 'write_file' action. Defaults to None.

        Returns:
            Dict[str, Any]: A dictionary containing the status ('success' or 'error')
                            and either 'result' (on success) or 'error_message' (on error).
        """
        logger.debug(f"FileSystemTool executing: action='{action}', path='{path}', content_present={content is not None}")
        try:
            target_path = self._validate_path(path)
            relative_path_for_log = os.path.relpath(target_path, self.root_dir)

            if action == 'list_directory':
                if not os.path.isdir(target_path):
                     if os.path.exists(target_path): raise OperationFailedError(f"Path '{relative_path_for_log}' is a file, not a directory.")
                     else: raise OperationFailedError(f"Directory '{relative_path_for_log}' not found.")
                try:
                    entries = os.listdir(target_path)
                    formatted_entries = [ name + '/' if os.path.isdir(os.path.join(target_path, name)) else name for name in entries ]
                    result_str = f"Contents of '{relative_path_for_log}':\n" + "\n".join(formatted_entries)
                    logger.info(f"Listed directory '{relative_path_for_log}'. Found {len(formatted_entries)} entries.")
                    return {"status": "success", "result": result_str}
                except Exception as e: raise OperationFailedError(f"Failed to list directory '{relative_path_for_log}': {e}") from e

            elif action == 'read_file':
                if not os.path.isfile(target_path):
                     if os.path.isdir(target_path): raise OperationFailedError(f"Path '{relative_path_for_log}' is a directory, not a file.")
                     else: raise OperationFailedError(f"File '{relative_path_for_log}' not found.")
                try:
                    with open(target_path, 'r', encoding='utf-8') as f: file_content = f.read()
                    logger.info(f"Read file '{relative_path_for_log}'.")
                    max_len = 1000
                    if len(file_content) > max_len: result_str = f"Content of '{relative_path_for_log}' (truncated):\n{file_content[:max_len]}..."
                    else: result_str = f"Content of '{relative_path_for_log}':\n{file_content}"
                    return {"status": "success", "result": result_str}
                except Exception as e: raise OperationFailedError(f"Failed to read file '{relative_path_for_log}': {e}") from e

            elif action == 'write_file':
                if content is None: raise ValueError("Content is required for 'write_file' action.")
                parent_dir = os.path.dirname(target_path)
                try:
                    if not os.path.exists(parent_dir):
                         os.makedirs(parent_dir); logger.info(f"Created directory '{os.path.relpath(parent_dir, self.root_dir)}' for writing file.")
                    elif not os.path.isdir(parent_dir): raise OperationFailedError(f"Cannot write file. Path component '{os.path.relpath(parent_dir, self.root_dir)}' exists but is not a directory.")
                    with open(target_path, 'w', encoding='utf-8') as f: f.write(content)
                    logger.info(f"Wrote content to file '{relative_path_for_log}'.")
                    return {"status": "success", "result": f"Successfully wrote content to '{relative_path_for_log}'."}
                except Exception as e: raise OperationFailedError(f"Failed to write file '{relative_path_for_log}': {e}") from e
            else:
                raise ValueError(f"Invalid action '{action}' passed to execute method.")

        except (FileSystemError, ValueError) as e:
            logger.error(f"FileSystemTool Error: {e}")
            return {"status": "error", "error_message": str(e)}
        except Exception as e:
            logger.error(f"FileSystemTool Unexpected Error: {e}", exc_info=True)
            return {"status": "error", "error_message": f"An unexpected error occurred: {e}"}

