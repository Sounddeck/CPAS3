"""
Module Registry for CPAS
Handles dynamic loading/unloading of application modules
"""
import os
import sys
import importlib
import inspect
import json
import logging
from typing import Dict, Any, Type, Optional, List, Callable

from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

class ModuleInfo:
    """Information about a registered module"""
    
    def __init__(self, 
                 module_id: str,
                 name: str,
                 description: str,
                 version: str,
                 author: str,
                 main_class: Type,
                 icon_path: Optional[str] = None,
                 dependencies: List[str] = None,
                 settings: Dict[str, Any] = None):
        self.module_id = module_id
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.main_class = main_class
        self.icon_path = icon_path
        self.dependencies = dependencies or []
        self.settings = settings or {}
        self.instance = None
        self.status = "registered"  # registered, loaded, active, error
        self.error_message = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "module_id": self.module_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "icon_path": self.icon_path,
            "dependencies": self.dependencies,
            "settings": self.settings,
            "status": self.status
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any], main_class: Type) -> 'ModuleInfo':
        """Create from dictionary"""
        return cls(
            module_id=data["module_id"],
            name=data["name"],
            description=data["description"],
            version=data["version"],
            author=data["author"],
            main_class=main_class,
            icon_path=data.get("icon_path"),
            dependencies=data.get("dependencies", []),
            settings=data.get("settings", {})
        )

class ModuleRegistry:
    """Registry for CPAS modules"""
    
    def __init__(self):
        """Initialize the module registry"""
        self.modules: Dict[str, ModuleInfo] = {}
        self.module_paths = []
        self.event_handlers = {}
        logger.info("Module registry initialized")
        
    def add_module_path(self, path: str) -> None:
        """Add a path to search for modules"""
        if path not in self.module_paths and os.path.isdir(path):
            self.module_paths.append(path)
            logger.info(f"Added module path: {path}")
            
    def discover_modules(self) -> List[str]:
        """Discover modules in registered paths"""
        discovered_modules = []
        
        for path in self.module_paths:
            # Check for module directories (must contain module.json)
            for item in os.listdir(path):
                module_dir = os.path.join(path, item)
                manifest_path = os.path.join(module_dir, "module.json")
                
                if os.path.isdir(module_dir) and os.path.exists(manifest_path):
                    try:
                        # Load manifest
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                            
                        # Check for module ID
                        module_id = manifest.get("module_id")
                        if not module_id:
                            logger.warning(f"Module in {module_dir} has no module_id in manifest")
                            continue
                            
                        # Register module
                        if self.register_module_from_manifest(manifest, module_dir):
                            discovered_modules.append(module_id)
                            
                    except Exception as e:
                        logger.error(f"Error loading module manifest from {manifest_path}: {e}")
        
        return discovered_modules
    
    def register_module_from_manifest(self, manifest: Dict[str, Any], module_dir: str) -> bool:
        """Register a module from its manifest"""
        try:
            module_id = manifest.get("module_id")
            main_module = manifest.get("main_module")
            main_class = manifest.get("main_class")
            
            if not all([module_id, main_module, main_class]):
                logger.warning(f"Invalid manifest for module {module_dir}")
                return False
                
            # Add module directory to path
            if module_dir not in sys.path:
                sys.path.append(module_dir)
                
            # Import the module
            module = importlib.import_module(main_module)
            cls = getattr(module, main_class)
            
            # Register the module
            self.register_module(
                module_id=module_id,
                name=manifest.get("name", module_id),
                description=manifest.get("description", ""),
                version=manifest.get("version", "1.0"),
                author=manifest.get("author", "Unknown"),
                main_class=cls,
                icon_path=os.path.join(module_dir, manifest.get("icon", "")),
                dependencies=manifest.get("dependencies", []),
                settings=manifest.get("settings", {})
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error registering module {module_dir}: {e}")
            return False
    
    def register_module(self, 
                        module_id: str,
                        name: str,
                        description: str,
                        version: str,
                        author: str,
                        main_class: Type,
                        icon_path: Optional[str] = None,
                        dependencies: List[str] = None,
                        settings: Dict[str, Any] = None) -> bool:
        """Register a module with the registry"""
        if module_id in self.modules:
            logger.warning(f"Module {module_id} is already registered")
            return False
            
        # Ensure main class is a QWidget or has a get_widget method
        if not (issubclass(main_class, QWidget) or hasattr(main_class, "get_widget")):
            logger.error(f"Module {module_id} main class must be a QWidget or have get_widget method")
            return False
            
        # Create module info
        module_info = ModuleInfo(
            module_id=module_id,
            name=name,
            description=description,
            version=version,
            author=author,
            main_class=main_class,
            icon_path=icon_path,
            dependencies=dependencies,
            settings=settings
        )
        
        # Add to registry
        self.modules[module_id] = module_info
        logger.info(f"Registered module: {name} ({module_id}) v{version}")
        
        # Fire event
        self.trigger_event("module_registered", module_id=module_id)
        
        return True
    
    def load_module(self, module_id: str) -> bool:
        """Load a module by ID"""
        if module_id not in self.modules:
            logger.error(f"Module {module_id} not found in registry")
            return False
            
        module_info = self.modules[module_id]
        
        # Check if already loaded
        if module_info.instance is not None:
            logger.info(f"Module {module_id} is already loaded")
            return True
            
        # Check dependencies
        for dep in module_info.dependencies:
            if dep not in self.modules:
                logger.error(f"Module {module_id} depends on {dep} which is not registered")
                module_info.status = "error"
                module_info.error_message = f"Missing dependency: {dep}"
                return False
                
            # Load dependency if needed
            dep_info = self.modules[dep]
            if dep_info.instance is None:
                if not self.load_module(dep):
                    logger.error(f"Failed to load dependency {dep} for module {module_id}")
                    module_info.status = "error"
                    module_info.error_message = f"Failed to load dependency: {dep}"
                    return False
        
        try:
            # Create instance
            module_info.instance = module_info.main_class()
            module_info.status = "loaded"
            
            # Fire event
            self.trigger_event("module_loaded", module_id=module_id)
            
            logger.info(f"Loaded module: {module_info.name} ({module_id})")
            return True
        except Exception as e:
            logger.error(f"Error loading module {module_id}: {e}")
            module_info.status = "error"
            module_info.error_message = str(e)
            return False
    
    def unload_module(self, module_id: str) -> bool:
        """Unload a module by ID"""
        if module_id not in self.modules:
            logger.error(f"Module {module_id} not found in registry")
            return False
            
        module_info = self.modules[module_id]
        
        # Check if loaded
        if module_info.instance is None:
            logger.info(f"Module {module_id} is not loaded")
            return True
            
        # Check if other modules depend on this one
        for other_id, other_info in self.modules.items():
            if module_id in other_info.dependencies and other_info.instance is not None:
                logger.error(f"Cannot unload {module_id}: module {other_id} depends on it")
                return False
                
        try:
            # Call cleanup if available
            if hasattr(module_info.instance, "cleanup"):
                module_info.instance.cleanup()
                
            # Remove instance
            module_info.instance = None
            module_info.status = "registered"
            
            # Fire event
            self.trigger_event("module_unloaded", module_id=module_id)
            
            logger.info(f"Unloaded module: {module_info.name} ({module_id})")
            return True
        except Exception as e:
            logger.error(f"Error unloading module {module_id}: {e}")
            module_info.status = "error"
            module_info.error_message = str(e)
            return False
    
    def get_module_instance(self, module_id: str) -> Optional[Any]:
        """Get a module instance by ID"""
        if module_id not in self.modules:
            return None
            
        module_info = self.modules[module_id]
        return module_info.instance
    
    def get_module_widget(self, module_id: str) -> Optional[QWidget]:
        """Get a module's widget by ID"""
        instance = self.get_module_instance(module_id)
        if instance is None:
            return None
            
        if isinstance(instance, QWidget):
            return instance
        elif hasattr(instance, "get_widget"):
            return instance.get_widget()
        
        return None
    
    def list_modules(self) -> List[Dict[str, Any]]:
        """List all registered modules"""
        return [module_info.to_dict() for module_info in self.modules.values()]
    
    def register_event_handler(self, event: str, handler: Callable) -> None:
        """Register a handler for an event"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    def trigger_event(self, event: str, **kwargs) -> None:
        """Trigger an event with the given arguments"""
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    handler(**kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler for {event}: {e}")

# Create singleton instance
module_registry = ModuleRegistry()
