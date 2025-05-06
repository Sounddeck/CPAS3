"""
Agent Module UI for CPAS Desktop
Provides interface for creating and managing AI agents
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QTabWidget, QSplitter, QComboBox, QLineEdit, 
    QTextEdit, QDialog, QFormLayout, QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont

from modules.agent.agent_manager import agent_manager
import modules.agent.agent_registry  # Import to register agents

class AgentListItem(QWidget):
    """Widget to display an agent in a list"""
    
    def __init__(self, agent_id, name, description, is_running, parent=None):
        super().__init__(parent)
        self.agent_id = agent_id
        self.is_running = is_running
        
        # Set up layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add name
        name_label = QLabel(name)
        name_label.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(name_label)
        
        # Add description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Add status
        status_text = "Running" if is_running else "Stopped"
        status_color = "#4CAF50" if is_running else "#F44336"
        status_label = QLabel(f"Status: <span style='color:{status_color};'>{status_text}</span>")
        layout.addWidget(status_label)
        
        # Style
        self.setStyleSheet("""
            AgentListItem {
                background-color: #2D2D30;
                border-radius: 5px;
                padding: 5px;
            }
        """)

class CreateAgentDialog(QDialog):
    """Dialog for creating a new agent"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Create Agent")
        self.setMinimumWidth(400)
        
        # Set up layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form layout for inputs
        form = QFormLayout()
        
        # Agent type
        self.type_combo = QComboBox()
        agent_types = agent_manager.list_agent_types()
        for type_id, type_desc in agent_types.items():
            self.type_combo.addItem(type_desc, type_id)
        form.addRow("Agent Type:", self.type_combo)
        
        # Agent name
        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)
        
        # Agent ID
        self.id_edit = QLineEdit()
        form.addRow("ID:", self.id_edit)
        
        # Description
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        form.addRow("Description:", self.desc_edit)
        
        layout.addLayout(form)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        # Style
        self.setStyleSheet("""
            QDialog {
                background-color: #252526;
                color: #FFFFFF;
            }
            
            QLabel {
                color: #FFFFFF;
            }
            
            QLineEdit, QTextEdit {
                background-color: #333333;
                border: 1px solid #3F3F46;
                border-radius: 3px;
                color: #FFFFFF;
                padding: 5px;
            }
            
            QComboBox {
                background-color: #333333;
                border: 1px solid #3F3F46;
                border-radius: 3px;
                padding: 5px;
                color: #FFFFFF;
            }
            
            QPushButton {
                background-color: #0E639C;
                border: none;
                border-radius: 3px;
                color: white;
                padding: 5px 10px;
            }
            
            QPushButton:hover {
                background-color: #1177BB;
            }
        """)
"""
Agent Module UI for CPAS Desktop
Provides interface for creating and managing AI agents
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QTabWidget, QSplitter, QComboBox, QLineEdit, 
    QTextEdit, QDialog, QFormLayout, QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QFont

from modules.agent.agent_manager import agent_manager
import modules.agent.agent_registry  # Import to register agents

class AgentListItem(QWidget):
    """Widget to display an agent in a list"""
    
    def __init__(self, agent_id, name, description, is_running, parent=None):
        super().__init__(parent)
        self.agent_id = agent_id
        self.is_running = is_running
        
        # Set up layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add name
        name_label = QLabel(name)
        name_label.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(name_label)
        
        # Add description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Add status
        status_text = "Running" if is_running else "Stopped"
        status_color = "#4CAF50" if is_running else "#F44336"
        status_label = QLabel(f"Status: <span style='color:{status_color};'>{status_text}</span>")
        layout.addWidget(status_label)
        
        # Style
        self.setStyleSheet("""
            AgentListItem {
                background-color: #2D2D30;
                border-radius: 5px;
                padding: 5px;
            }
        """)

class CreateAgentDialog(QDialog):
    """Dialog for creating a new agent"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Create Agent")
        self.setMinimumWidth(400)
        
        # Set up layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form layout for inputs
        form = QFormLayout()
        
        # Agent type
        self.type_combo = QComboBox()
        agent_types = agent_manager.list_agent_types()
        for type_id, type_desc in agent_types.items():
            self.type_combo.addItem(type_desc, type_id)
        form.addRow("Agent Type:", self.type_combo)
        
        # Agent name
        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)
        
        # Agent ID
        self.id_edit = QLineEdit()
        form.addRow("ID:", self.id_edit)
        
        # Description
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        form.addRow("Description:", self.desc_edit)
        
        layout.addLayout(form)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        # Style
        self.setStyleSheet("""
            QDialog {
                background-color: #252526;
                color: #FFFFFF;
            }
            
            QLabel {
                color: #FFFFFF;
            }
            
            QLineEdit, QTextEdit {
                background-color: #333333;
                border: 1px solid #3F3F46;
                border-radius: 3px;
                color: #FFFFFF;
                padding: 5px;
            }
            
            QComboBox {
                background-color: #333333;
                border: 1px solid #3F3F46;
                border-radius: 3px;
                padding: 5px;
                color: #FFFFFF;
            }
            
            QPushButton {
                background-color: #0E639C;
                border: none;
                border-radius: 3px;
                color: white;
                padding: 5px 10px;
            }
            
            QPushButton:hover {
                background-color: #1177BB;
            }
        """)
