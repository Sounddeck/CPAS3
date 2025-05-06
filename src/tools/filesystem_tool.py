"""
File System Tool for CPAS3
Provides file and directory manipulation capabilities
"""
import os
import logging
from typing import List, Dict, Any, Optional
from langchain.tools import BaseTool, tool

logger = logging.getLogger(__name__)

@tool
def list_directory(directory_path: str) -> str:
    """
    List files and directories in the specified path.
    
    Args:
        directory_path: The directory path to list contents from.
        
    Returns:
        A string containing the directory contents.
    """
    try:
        # Expand user directory if needed (e.g., ~/)
        directory_path = os.path.expanduser(directory_path)
        
        # Check if directory exists
        if not os.path.exists(directory_path):
            return f"Error: Directory '{directory_path}' does not exist."
        
        # Check if path is a directory
        if not os.path.isdir(directory_path):
            return f"Error: '{directory_path}' is not a directory."
        
        # List directory contents
        contents = os.listdir(directory_path)
        
        # Separate files and directories
        directories = []
        files = []
        
        for item in contents:
            item_path = os.path.join(directory_path, item)
            if os.path.isdir(item_path):
                directories.append(f"📁 {item}/")
            else:
                files.append(f"📄 {item}")
        
        # Sort alphabetically
        directories.sort()
        files.sort()
        
        # Build result
        result = f"Contents of {directory_path}:\n\n"
        
        if directories:
            result += "Directories:\n"
            result += "\n".join(directories)
            result += "\n\n"
        
        if files:
            result += "Files:\n"
            result += "\n".join(files)
        
        if not directories and not files:
            result += "Directory is empty."
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing directory: {e}")
        return f"Error: {str(e)}"

@tool
def read_file(file_path: str) -> str:
    """
    Read the contents of a text file.
    
    Args:
        file_path: The path to the file to read.
        
    Returns:
        The contents of the file as a string.
    """
    try:
        # Expand user directory if needed (e.g., ~/)
        file_path = os.path.expanduser(file_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist."
        
        # Check if path is a file
        if not os.path.isfile(file_path):
            return f"Error: '{file_path}' is not a file."
        
        # Check if file is too large (>1MB)
        if os.path.getsize(file_path) > 1024 * 1024:
            return f"Error: File '{file_path}' is too large to read (>1MB)."
        
        # Read file
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return f"Contents of {file_path}:\n\n{content}"
        
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return f"Error: {str(e)}"

@tool
def write_file(file_path: str, content: str) -> str:
    """
    Write content to a text file.
    
    Args:
        file_path: The path to the file to write.
        content: The content to write to the file.
        
    Returns:
        A success or error message.
    """
    try:
        # Expand user directory if needed (e.g., ~/)
        file_path = os.path.expanduser(file_path)
        
        # Create directories if they don't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Successfully wrote to file: {file_path}"
        
    except Exception as e:
        logger.error(f"Error writing file: {e}")
        return f"Error: {str(e)}"

@tool
def create_directory(directory_path: str) -> str:
    """
    Create a new directory.
    
    Args:
        directory_path: The path of the directory to create.
        
    Returns:
        A success or error message.
    """
    try:
        # Expand user directory if needed (e.g., ~/)
        directory_path = os.path.expanduser(directory_path)
        
        # Check if directory already exists
        if os.path.exists(directory_path):
            return f"Directory '{directory_path}' already exists."
        
        # Create directory
        os.makedirs(directory_path)
        
        return f"Successfully created directory: {directory_path}"
        
    except Exception as e:
        logger.error(f"Error creating directory: {e}")
        return f"Error: {str(e)}"
