#!/usr/bin/env python3
"""
CPAS Desktop - Cognitive Processing Automation System
Main application entry point
"""

import sys
import logging
import os
import traceback
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QStackedWidget,
    QToolBar, QLabel, QVBoxLayout, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CPASDesktop(QMainWindow):
    """Main CPAS Desktop application window"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("CPAS3 Desktop")
        self.resize(1200, 800)
        
        # Set the central widget
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create an empty widget as a placeholder
        self.placeholder = QWidget()
        placeholder_layout = QVBoxLayout()
        placeholder_label = QLabel("Select a module from the dock")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)
        self.placeholder.setLayout(placeholder_layout)
        
        # Add the placeholder to the central widget
        self.central_widget.addWidget(self.placeholder)
        self.central_widget.setCurrentWidget(self.placeholder)
        
        # Set up the dock
        self.dock = QToolBar("Modules")
        self.dock.setIconSize(QSize(32, 32))
        self.dock.setMovable(False)
        self.dock.setOrientation(Qt.Orientation.Horizontal)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.dock)
        
        # Initialize class properties
        self.loaded_modules = {}
        self.active_module = None
        self.module_loader = None
        
        # Load modules
        print("DEBUG: About to load modules")
        self.load_modules()
        
        # Status bar
        self.statusBar().showMessage("CPAS3 Desktop Ready")
        
        logger.info("CPAS3 Desktop initialized")

    def load_modules(self):
        """Load all available modules"""
        try:
            # Import module loader
            print("DEBUG: Importing ModuleLoader")
            from modules.module_loader import ModuleLoader
            self.module_loader = ModuleLoader()
            
            # Discover modules
            print("DEBUG: Starting module discovery")
            modules = self.module_loader.discover_modules()
            
            # Debug output
            print(f"DEBUG: Found {len(modules)} modules")
            for module_info in modules:
                print(f"DEBUG: Module found - ID: {module_info.get('module_id')}, Name: {module_info.get('name')}")
            
            if not modules:
                print("DEBUG: No modules were found")
                return
            
            # Process each module
            for module_info in modules:
                try:
                    # Get module info
                    module_id = module_info.get("module_id", "unknown")
                    module_name = module_info.get("name", "Unnamed Module")
                    module_description = module_info.get("description", "")
                    module_icon_path = module_info.get("icon", None)
                    module_path = module_info.get("path", None)
                    
                    print(f"DEBUG: Processing module {module_name} ({module_id})")
                    
                    # Create action for the dock
                    action = QAction(module_name, self)
                    action.setStatusTip(module_description)
                    action.setData(module_id)
                    
                    # Set icon if available
                    if module_icon_path and os.path.exists(os.path.join(module_path, module_icon_path)):
                        icon_path = os.path.join(module_path, module_icon_path)
                        action.setIcon(QIcon(icon_path))
                        print(f"DEBUG: Set icon from {icon_path}")
                    else:
                        print(f"DEBUG: No icon found at {os.path.join(module_path, module_icon_path) if module_icon_path else 'None'}")
                    
                    # THIS IS THE KEY FIX - Using lambda to properly capture module_id
                    action.triggered.connect(lambda checked=False, mid=module_id: self.activate_module(mid))
                    
                    # Add to dock
                    self.dock.addAction(action)
                    print(f"DEBUG: Added module {module_name} to dock")
                    
                    # Store module info
                    self.loaded_modules[module_id] = {
                        "info": module_info,
                        "instance": None,
                        "action": action
                    }
                    
                    logger.info(f"Module loaded: {module_name} ({module_id})")
                    
                except Exception as e:
                    print(f"DEBUG: Error processing module: {str(e)}")
                    traceback.print_exc()
                    logger.error(f"Error loading module: {e}")
        
        except Exception as e:
            print(f"DEBUG: Module loading error: {str(e)}")
            traceback.print_exc()
            logger.error(f"Error in module loading: {e}")

    def activate_module(self, module_id):
        """Activate a module by its ID"""
        try:
            print(f"DEBUG: Activating module: {module_id}")
            
            # If this module is already active, do nothing
            if self.active_module == module_id:
                print(f"DEBUG: Module {module_id} is already active")
                return
            
            # Look up the module data
            module_data = self.loaded_modules.get(module_id, None)
            if not module_data:
                print(f"DEBUG: Module {module_id} not found in loaded_modules")
                QMessageBox.warning(self, "Module Error", f"Module not found: {module_id}")
                return
            
            # Create module instance if it doesn't exist
            if not module_data["instance"]:
                try:
                    print(f"DEBUG: Creating instance of module {module_id}")
                    instance = self.module_loader.instantiate_module(module_data["info"])
                    if instance:
                        print(f"DEBUG: Successfully created instance of {module_id}")
                        module_data["instance"] = instance
                        self.central_widget.addWidget(instance)
                        print(f"DEBUG: Added module widget to central_widget")
                    else:
                        print(f"DEBUG: Failed to create instance of module {module_id}")
                        QMessageBox.critical(
                            self,
                            "Module Error",
                            f"Failed to instantiate module: {module_id}"
                        )
                        return
                except Exception as e:
                    print(f"DEBUG: Error initializing module {module_id}: {str(e)}")
                    traceback.print_exc()
                    QMessageBox.critical(
                        self,
                        "Module Error",
                        f"Error initializing module {module_id}: {str(e)}"
                    )
                    logger.error(f"Error initializing module {module_id}: {e}")
                    return
            
            # Activate the module
            print(f"DEBUG: Setting current widget to module {module_id}")
            self.central_widget.setCurrentWidget(module_data["instance"])
            self.active_module = module_id
            
            self.statusBar().showMessage(f"Active module: {module_data['info']['name']}")
            logger.info(f"Activated module: {module_id}")
        except Exception as e:
            print(f"DEBUG: Error in activate_module: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Module Error",
                f"Error activating module: {str(e)}"
            )

def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("CPAS3 Desktop")
    app.setStyle("Fusion")  # Use Fusion style for consistent look across platforms
    
    # Set the app style to dark mode
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }
        
        QMenuBar, QToolBar {
            background-color: #252526;
            color: #FFFFFF;
        }
        
        QMenuBar::item:selected, QToolBar::item:selected {
            background-color: #3F3F46;
        }
        
        QToolBar {
            border-top: 1px solid #3F3F46;
        }
        
        QStatusBar {
            background-color: #252526;
            color: #CCCCCC;
        }
    """)
    
    # Create and show the main window
    main_window = CPASDesktop()
    main_window.show()
    
    # Run the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
