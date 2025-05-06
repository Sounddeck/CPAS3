"""
File System Tool for CPAS Agents
Provides file operations capabilities to agents
"""
import os
import logging
from typing import Dict, Any, List, Optional
import json

from modules.agent.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class FileSystemTool(BaseTool):
    """Tool for interacting with the file system"""
    
    def __init__(self):
        """Initialize the file system tool"""
        super().__init__(
            tool_id="file_system_tool",
            name="File System",
            description="Access and manipulate files and directories"
        )
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a file system operation
        
        Args:
            params: Parameters including:
                - action: Operation to perform
                - path: File or directory path
                - content: Content for file operations (optional)
                
        Returns:
            Result of the operation
        """
        action = params.get("action", "")
        path = params.get("path", "")
        
        if not action or not path:
            return {"error": "Missing required parameters: action, path"}
        
        try:
            # Dispatch to appropriate handler
            if action == "read_file":
                return await self._read_file(path)
            elif action == "write_file":
                content = params.get("content", "")
                return await self._write_file(path, content)
            elif action == "list_directory":
                return await self._list_directory(path)
            elif action == "create_directory":
                return await self._create_directory(path)
            elif action == "delete":
                return await self._delete(path)
            else:
                return {"error": f"Unknown action: {action}"}
        
        except Exception as e:
            logger.error(f"File system operation error: {e}")
            return {"error": str(e)}
    
    async def _read_file(self, path: str) -> Dict[str, Any]:
        """Read a file's contents
        
        Args:
            path: Path to the file
            
        Returns:
            File contents
        """
        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}
        
        if not os.path.isfile(path):
            return {"error": f"Path is not a file: {path}"}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "path": path
            }
        except Exception as e:
            return {"error": f"Failed to read file: {e}"}
    
    async def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file
        
        Args:
            path: Path to the file
            content: Content to write
            
        Returns:
            Operation result
        """
        try:
            # Create directory if it doesn't exist
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": path,
                "bytes_written": len(content)
            }
        except Exception as e:
            return {"error": f"Failed to write file: {e}"}
    
    async def _list_directory(self, path: str) -> Dict[str, Any]:
        """List contents of a directory
        
        Args:
            path: Directory path
            
        Returns:
            Directory contents
        """
        if not os.path.exists(path):
            return {"error": f"Directory not found: {path}"}
        
        if not os.path.isdir(path):
            return {"error": f"Path is not a directory: {path}"}
        
        try:
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                items.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None
                })
            
            return {
                "success": True,
                "path": path,
                "items": items
            }
        except Exception as e:
            return {"error": f"Failed to list directory: {e}"}
    
    async def _create_directory(self, path: str) -> Dict[str, Any]:
        """Create a directory
        
        Args:
            path: Directory path
            
        Returns:
            Operation result
        """
        try:
            if os.path.exists(path):
                return {"error": f"Path already exists: {path}"}
            
            os.makedirs(path)
            
            return {
                "success": True,
                "path": path
            }
        except Exception as e:
            return {"error": f"Failed to create directory: {e}"}
    
    async def _delete(self, path: str) -> Dict[str, Any]:
        """Delete a file or directory
        
        Args:
            path: Path to delete
            
        Returns:
            Operation result
        """
        if not os.path.exists(path):
            return {"error": f"Path not found: {path}"}
        
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                # Directory - check if empty
                if not os.listdir(path):
                    os.rmdir(path)
                else:
                    return {"error": f"Directory not empty: {path}"}
            
            return {
                "success": True,
                "path": path
            }
        except Exception as e:
            return {"error": f"Failed to delete: {e}"}
