"""
Shell command tool for agents
Allows agents to run shell commands
"""

import os
import subprocess
import logging
import shlex
import threading
import time
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class ShellTool:
    """Tool for executing shell commands"""
    
    def __init__(self, working_dir: str = None, timeout: int = 30):
        """Initialize the shell tool"""
        self.working_dir = working_dir or os.getcwd()
        self.timeout = timeout
        self.current_process = None
        logger.info(f"Shell tool initialized with working directory: {self.working_dir}")
    
    def execute(self, command: str, capture_output: bool = True) -> Dict[str, Any]:
        """
        Execute a shell command
        
        Args:
            command: The command to execute
            capture_output: Whether to capture and return stdout/stderr
            
        Returns:
            Dictionary with command results
        """
        try:
            logger.info(f"Executing command: {command}")
            
            # Use shlex to properly handle command arguments
            args = shlex.split(command)
            
            # Execute the command
            start_time = time.time()
            
            self.current_process = subprocess.Popen(
                args,
                cwd=self.working_dir,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                text=True,
                shell=False  # Safer to not use shell=True
            )
            
            stdout, stderr = self.current_process.communicate(timeout=self.timeout)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Prepare result
            result = {
                "command": command,
                "exit_code": self.current_process.returncode,
                "duration": duration,
                "success": self.current_process.returncode == 0
            }
            
            if capture_output:
                result["stdout"] = stdout
                result["stderr"] = stderr
                
            self.current_process = None
            logger.info(f"Command completed with exit code: {result['exit_code']}")
            return result
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {self.timeout} seconds: {command}")
            if self.current_process:
                self.current_process.kill()
                stdout, stderr = self.current_process.communicate()
                self.current_process = None
                
            return {
                "command": command,
                "exit_code": -1,
                "duration": self.timeout,
                "success": False,
                "error": "Command timed out",
                "stdout": stdout if capture_output else None,
                "stderr": stderr if capture_output else None
            }
            
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            if self.current_process:
                try:
                    self.current_process.kill()
                except:
                    pass
                self.current_process = None
                
            return {
                "command": command,
                "exit_code": -1,
                "success": False,
                "error": str(e),
                "stdout": None,
                "stderr": None
            }
    
    def cancel_current(self) -> bool:
        """Cancel the current command execution if any"""
        if self.current_process:
            try:
                self.current_process.kill()
                logger.info("Killed running process")
                self.current_process = None
                return True
            except Exception as e:
                logger.error(f"Error cancelling command: {str(e)}")
                return False
        return False
