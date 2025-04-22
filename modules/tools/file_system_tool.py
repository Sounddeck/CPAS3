import os
import logging
from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

# Define potential errors for clarity
class FileSystemError(Exception):
    pass
class PathTraversalError(FileSystemError):
    pass
class OperationFailedError(FileSystemError):
    pass

class FileSystemTool(BaseTool):
    """
    Tool for interacting with a restricted file system workspace.
    Input format is a single string: 'action:path' or 'action:path::content'.
    Valid actions: 'list_directory', 'read_file', 'write_file'.
    Example Input 1: list_directory:./subfolder
    Example Input 2: read_file:/path/within/workspace/file.txt
    Example Input 3: write_file:/path/to/save/file.txt::This is the content to write.
    Paths MUST be relative to the workspace root and cannot contain '..'.
    """
    name: str = "file_system_tool"
    description: str = (
        "Interacts with a restricted file system workspace. "
        "Input format: 'action:path' or 'action:path::content'. "
        "Valid actions: 'list_directory', 'read_file', 'write_file'. "
        "Paths MUST be relative to the workspace root and cannot contain '..'. "
        "Example 1: list_directory:./subfolder "
        "Example 2: read_file:file.txt "
        "Example 3: write_file:new_notes.txt::Write this text."
    )
    root_dir: str

    def _validate_path(self, path: str) -> str:
        """Validates and resolves the path within the root directory."""
        if not path:
            raise PathTraversalError("Path cannot be empty.")
        if ".." in path.split(os.path.sep):
            raise PathTraversalError("Path cannot contain '..'. Access denied.")

        # Resolve the path relative to the root directory
        # os.path.join handles leading './' correctly
        # os.path.abspath ensures we have a full path for comparison
        full_path = os.path.abspath(os.path.join(self.root_dir, path))

        # Check if the resolved path is still within the root directory
        if not full_path.startswith(os.path.abspath(self.root_dir)):
            raise PathTraversalError(f"Path '{path}' resolves outside the allowed workspace. Access denied.")

        return full_path

    def _run(self, tool_input: str) -> str:
        """
        Executes the file system action based on the formatted input string.
        Format: 'action:path' or 'action:path::content'.
        """
        logger.debug(f"FileSystemTool received input: '{tool_input}'")
        try:
            parts = tool_input.split('::', 1)
            action_path = parts[0]
            content = parts[1] if len(parts) > 1 else None

            action_parts = action_path.split(':', 1)
            if len(action_parts) != 2:
                raise ValueError("Invalid input format. Expected 'action:path' or 'action:path::content'.")

            action, path_str = action_parts
            action = action.strip()
            path_str = path_str.strip()

            logger.debug(f"Parsed action: '{action}', path: '{path_str}', content present: {content is not None}")

            # Validate action
            allowed_actions = ['list_directory', 'read_file', 'write_file']
            if action not in allowed_actions:
                raise ValueError(f"Invalid action '{action}'. Allowed actions are: {', '.join(allowed_actions)}")

            # Validate and resolve path (relative to root_dir)
            target_path = self._validate_path(path_str)
            relative_path_for_log = os.path.relpath(target_path, self.root_dir) # For logging clarity

            # --- Execute Action ---
            if action == 'list_directory':
                if not os.path.isdir(target_path):
                     # Check if it's a file, provide specific error
                     if os.path.exists(target_path):
                          raise OperationFailedError(f"Path '{relative_path_for_log}' is a file, not a directory. Cannot list contents.")
                     else:
                          raise OperationFailedError(f"Directory '{relative_path_for_log}' not found.")
                try:
                    entries = os.listdir(target_path)
                    # Add '/' to directories for clarity in listing
                    formatted_entries = [
                        name + '/' if os.path.isdir(os.path.join(target_path, name)) else name
                        for name in entries
                    ]
                    result = f"Contents of '{relative_path_for_log}':\n" + "\n".join(formatted_entries)
                    logger.info(f"Listed directory '{relative_path_for_log}'. Found {len(formatted_entries)} entries.")
                    return result
                except Exception as e:
                    raise OperationFailedError(f"Failed to list directory '{relative_path_for_log}': {e}") from e

            elif action == 'read_file':
                if not os.path.isfile(target_path):
                     if os.path.isdir(target_path):
                          raise OperationFailedError(f"Path '{relative_path_for_log}' is a directory, not a file. Cannot read.")
                     else:
                          raise OperationFailedError(f"File '{relative_path_for_log}' not found.")
                try:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    logger.info(f"Read file '{relative_path_for_log}'.")
                    # Maybe truncate long files in output?
                    max_len = 1000
                    if len(file_content) > max_len:
                         return f"Content of '{relative_path_for_log}' (truncated):\n{file_content[:max_len]}..."
                    else:
                         return f"Content of '{relative_path_for_log}':\n{file_content}"
                except Exception as e:
                    raise OperationFailedError(f"Failed to read file '{relative_path_for_log}': {e}") from e

            elif action == 'write_file':
                if content is None:
                    raise ValueError("Content is required for 'write_file' action. Use '::' separator.")
                # Ensure parent directory exists
                parent_dir = os.path.dirname(target_path)
                try:
                    if not os.path.exists(parent_dir):
                         os.makedirs(parent_dir)
                         logger.info(f"Created directory '{os.path.relpath(parent_dir, self.root_dir)}' for writing file.")
                    elif not os.path.isdir(parent_dir):
                         raise OperationFailedError(f"Cannot write file. Path component '{os.path.relpath(parent_dir, self.root_dir)}' exists but is not a directory.")

                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"Wrote content to file '{relative_path_for_log}'.")
                    return f"Successfully wrote content to '{relative_path_for_log}'."
                except Exception as e:
                    raise OperationFailedError(f"Failed to write file '{relative_path_for_log}': {e}") from e

            else:
                # This should not be reachable due to earlier validation
                raise ValueError(f"Unhandled action: {action}")

        except FileSystemError as e: # Catch specific file system errors
            logger.error(f"FileSystemTool Error: {e}")
            return f"Error: {e}"
        except ValueError as e: # Catch input format errors
             logger.error(f"FileSystemTool Input Error: {e}")
             return f"Error: Invalid input format - {e}"
        except Exception as e: # Catch unexpected errors
            logger.error(f"FileSystemTool Unexpected Error: {e}", exc_info=True)
            return f"Error: An unexpected error occurred: {e}"

    # No async version implemented for now
    # async def _arun(self, tool_input: str) -> str:
    #     raise NotImplementedError("FileSystemTool does not support async")

    # args_schema is not strictly needed when _run takes a single string,
    # but can be useful for documentation/validation if desired later.
    # args_schema: Optional[Type[BaseModel]] = None
