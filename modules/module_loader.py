"""
Module loader for CPAS Desktop
Discovers and loads modules dynamically
"""
import os
import sys
import json
import importlib
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ModuleLoader:
    """Discovers and loads CPAS modules"""
    
    def __init__(self, modules_dir: str = "modules"):
        """Initialize the module loader
        
        Args:
            modules_dir: Directory containing modules
        """
        self.modules_dir = modules_dir
        
    def discover_modules(self) -> List[Dict[str, Any]]:
        """Discover available modules
        
        Returns:
            List of module information dictionaries
        """
        modules = []
        
        if not os.path.exists(self.modules_dir):
            logger.warning(f"Modules directory not found: {self.modules_dir}")
            return modules
        
        # Scan for module directories
        for item in os.listdir(self.modules_dir):
            module_path = os.path.join(self.modules_dir, item)
            
            # Skip files and hidden directories
            if not os.path.isdir(module_path) or item.startswith('.'):
                continue
                
            # Look for module.json
            module_json_path = os.path.join(module_path, "module.json")
            if not os.path.exists(module_json_path):
                continue
                
            try:
                # Load module info
                with open(module_json_path, 'r', encoding='utf-8') as f:
                    module_info = json.load(f)
                    
                # Add path to module info
                module_info["path"] = module_path
                
                # Add to list of modules
                modules.append(module_info)
                
            except Exception as e:
                logger.error(f"Error loading module info from {module_json_path}: {e}")
        
        return modules
    
    def instantiate_module(self, module_info: Dict[str, Any]) -> Optional[Any]:
        """Create an instance of a module
        
        Args:
            module_info: Module information dictionary
            
        Returns:
            Module instance or None if error
        """
        try:
            # Extract module info
            module_path = module_info.get("path", "")
            main_module = module_info.get("main_module", "")
            main_class = module_info.get("main_class", "")
            
            if not module_path or not main_module or not main_class:
                logger.error(f"Missing module info: path={module_path}, main_module={main_module}, main_class={main_class}")
                return None
            
            # Set up for import
            sys.path.append(os.path.abspath(os.path.dirname(module_path)))
            
            # Import the module
            module_import_path = f"modules.{os.path.basename(module_path)}.{main_module}"
            logger.debug(f"Importing module: {module_import_path}")
            
            module = importlib.import_module(module_import_path)
            
            # Get the main class
            class_obj = getattr(module, main_class)
            
            # Create instance
            instance = class_obj()
            
            return instance
            
        except Exception as e:
            logger.error(f"Error instantiating module: {e}")
            return None
