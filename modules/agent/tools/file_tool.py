import logging
import os
from typing import Type, Optional
from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

class FileToolInput(BaseModel):
    """Input schema for the FileTool."""
    action: str = Field(description="The action to perform: 'read', 'write', 'list', 'delete'")
    path: str = Field(description="Relative path to the file or directory within the allowed base directory.")
    content: Optional[str] = Field(None, description="Content to write to the file (only for 'write' action).")
    max_chars: Optional[int] = Field(None, description="Maximum number of characters to read (only for 'read' action).")

class FileTool(BaseTool):
    """
    A tool for interacting with the local file system within a specified base directory.
    Provides read, write, list, and delete operations.
    Paths are relative to the configured base directory.
    """
    name: str = "file_system_tool"
    description: str = (
        "Performs file operations (read, write, list, delete) within a restricted directory. "
        "Paths must be relative to the base directory. Use 'list' with path='.' to see the root contents."
    )
    args_schema: Type[BaseModel] = FileToolInput
    base_dir: str = Field(...) # Make base_dir a required field

    # --- Modified __init__ ---
    def __init__(self, base_dir: str, **kwargs):
        """
        Initializes the FileTool.

        Args:
            base_dir: The absolute path to the root directory the tool can operate within.
            **kwargs: Additional arguments passed to the parent class initializer.
        """
        # Ensure base_dir is absolute before passing to super
        abs_base_dir = os.path.abspath(base_dir)
        # Pass base_dir to super().__init__ for Pydantic validation
        super().__init__(base_dir=abs_base_dir, **kwargs)
        # self.base_dir is now set by Pydantic via super().__init__

        if not os.path.isdir(self.base_dir):
            # Or raise an error if the directory must exist
            logger.warning(f"FileTool base directory '{self.base_dir}' does not exist. It may need to be created.")
        logger.debug(f"FileTool initialized with base directory: {self.base_dir}")
    # --- End Modified __init__ ---


    def _run(self, action: str, path: str, content: Optional[str] = None, max_chars: Optional[int] = None) -> str:
        """Executes the specified file operation."""
        try:
            # --- Security Check: Ensure path is within base_dir ---
            # Use self.base_dir which is guaranteed to be set and absolute
            full_path = os.path.abspath(os.path.join(self.base_dir, path))
            if not full_path.startswith(self.base_dir):
                logger.warning(f"Attempted file access outside base directory: {path} (resolved to {full_path})")
                return f"Error: Access denied. Path '{path}' is outside the allowed directory."
            # --- End Security Check ---

            logger.info(f"Executing file tool action '{action}' on path '{path}' (full: {full_path})")

            if action == "read":
                if not os.path.exists(full_path):
                    return f"Error: File not found at '{path}'."
                if not os.path.isfile(full_path):
                     return f"Error: Path '{path}' is not a file."
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        if max_chars is not None and max_chars > 0:
                             file_content = f.read(max_chars)
                             if len(file_content) == max_chars:
                                  file_content += "..." # Indicate truncation
                        else:
                             file_content = f.read()
                    logger.debug(f"Read {len(file_content)} chars from '{path}'.")
                    return file_content
                except Exception as e:
                    logger.error(f"Error reading file '{path}': {e}", exc_info=True)
                    return f"Error reading file '{path}': {e}"

            elif action == "write":
                if content is None:
                    return "Error: Content must be provided for 'write' action."
                # Ensure parent directory exists
                parent_dir = os.path.dirname(full_path)
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.debug(f"Wrote {len(content)} chars to '{path}'.")
                    return f"Successfully wrote to file '{path}'."
                except Exception as e:
                    logger.error(f"Error writing file '{path}': {e}", exc_info=True)
                    return f"Error writing file '{path}': {e}"

            elif action == "list":
                if not os.path.exists(full_path):
                    return f"Error: Directory not found at '{path}'."
                if not os.path.isdir(full_path):
                     return f"Error: Path '{path}' is not a directory."
                try:
                    items = os.listdir(full_path)
                    logger.debug(f"Listed {len(items)} items in '{path}'.")
                    if not items:
                         return f"Directory '{path}' is empty."
                    # Add indicator for directories
                    output_items = []
                    for item in items:
                         item_path = os.path.join(full_path, item)
                         if os.path.isdir(item_path):
                              output_items.append(f"{item}/")
                         else:
                              output_items.append(item)
                    return "\n".join(output_items)
                except Exception as e:
                    logger.error(f"Error listing directory '{path}': {e}", exc_info=True)
                    return f"Error listing directory '{path}': {e}"

            elif action == "delete":
                 if not os.path.exists(full_path):
                      return f"Error: File or directory not found at '{path}'."
                 try:
                      if os.path.isfile(full_path):
                           os.remove(full_path)
                           logger.debug(f"Deleted file '{path}'.")
                           return f"Successfully deleted file '{path}'."
                      elif os.path.isdir(full_path):
                           # For safety, maybe only allow deleting empty dirs or disallow dir deletion?
                           # Let's disallow recursive deletion for now.
                           if os.listdir(full_path):
                                return f"Error: Directory '{path}' is not empty. Cannot delete non-empty directories."
                           os.rmdir(full_path)
                           logger.debug(f"Deleted empty directory '{path}'.")
                           return f"Successfully deleted empty directory '{path}'."
                      else:
                           return f"Error: Path '{path}' is neither a file nor a directory."
                 except Exception as e:
                      logger.error(f"Error deleting '{path}': {e}", exc_info=True)
                      return f"Error deleting '{path}': {e}"

            else:
                return f"Error: Unknown action '{action}'. Valid actions are: read, write, list, delete."

        except Exception as e:
            logger.error(f"Unexpected error in FileTool action '{action}' for path '{path}': {e}", exc_info=True)
            return f"An unexpected error occurred: {e}"

    async def _arun(self, action: str, path: str, content: Optional[str] = None, max_chars: Optional[int] = None) -> str:
        """Asynchronous version of the file operation (optional)."""
        # For simplicity, we run the synchronous version in a thread pool
        # If true async file I/O is needed, libraries like aiofiles would be used.
        # from langchain_core.runnables.config import run_in_executor
        # return await run_in_executor(None, self._run, action, path, content, max_chars)
        # For now, just call the sync version directly if async isn't critical
        logger.warning("FileTool._arun is using synchronous execution.")
        return self._run(action, path, content, max_chars)

