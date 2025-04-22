"""Module loader for CPAS Desktop"""
import os
import sys
import json
import importlib
import logging

logger = logging.getLogger(__name__)

class ModuleLoader:
    """Discovers and loads CPAS modules"""
    
    def __init__(self, modules_dir: str = "modules"):
        """Initialize the module loader"""
        self.modules_dir = modules_dir
        
    def discover_modules(self):
        """Discover available modules"""
        modules = []
        
        # Debug
        print(f"DEBUG: Looking for modules in {os.path.abspath(self.modules_dir)}")
        
        if not os.path.exists(self.modules_dir):
            logger.warning(f"Modules directory not found: {self.modules_dir}")
            return modules
        
        # List all items in modules directory
        for item in os.listdir(self.modules_dir):
            module_path = os.path.join(self.modules_dir, item)
            
            # Skip files and hidden directories
            if not os.path.isdir(module_path) or item.startswith('.'):
                continue
                
            # Look for module.json
            module_json_path = os.path.join(module_path, "module.json")
            if not os.path.exists(module_json_path):
                print(f"DEBUG: No module.json found in {module_path}")
                continue
                
            try:
                # Load module info
                with open(module_json_path, 'r', encoding='utf-8') as f:
                    module_info = json.load(f)
                    
                # Add path to module info
                module_info["path"] = module_path
                
                # Add to list of modules
                modules.append(module_info)
                print(f"DEBUG: Discovered module: {module_info.get('name')}")
                
            except Exception as e:
                logger.error(f"Error loading module info from {module_json_path}: {e}")
        
        return modules
    
    def instantiate_module(self, module_info):
        """Create an instance of a module"""
        try:
            # Extract module info
            module_path = module_info.get("path", "")
            main_module = module_info.get("main_module", "")
            main_class = module_info.get("main_class", "")
            
            if not module_path or not main_module or not main_class:
                logger.error(f"Missing module info: {module_info}")
                return None
            
            # Debug
            print(f"DEBUG: Attempting to import {main_module} from {module_path}")
            
            # Import the module
            module_import_path = f"modules.{os.path.basename(module_path)}.{main_module}"
            module = importlib.import_module(module_import_path)
            
            # Get the main class
            class_obj = getattr(module, main_class)
            
            # Create instance
            instance = class_obj()
            print(f"DEBUG: Successfully created instance of {main_class}")
            
            return instance
            
        except Exception as e:
            logger.error(f"Error instantiating module: {e}")
            print(f"DEBUG ERROR: {str(e)}")
            return None
