"""
Main window implementation for CPAS3
Provides the primary UI components
"""
import logging
from typing import Dict, Any, Optional, Callable

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QPushButton, QLabel, QSplitter, QMenu,
    QStatusBar, QToolBar, QAction, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QTextCursor

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main window for the CPAS application"""
    
    # Signals
    message_submitted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("CPAS Desktop")
        self.resize(1200, 800)
        
        # Set up UI components
        self._setup_ui()
        
        logger.debug("MainWindow initialized")
    
    def _setup_ui(self):
        """Set up the main UI components"""
        # Create central widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for chat and sidebar
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Chat area
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        
        # Message input area
        input_layout = QHBoxLayout()
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.setMaximumHeight(100)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._on_send_clicked)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        
        # Add widgets to chat layout
        chat_layout.addWidget(self.chat_display)
        chat_layout.addLayout(input_layout)
        
        # Sidebar area
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        
        sidebar_label = QLabel("Sidebar")
        sidebar_layout.addWidget(sidebar_label)
        
        # Add widgets to splitter
        splitter.addWidget(chat_widget)
        splitter.addWidget(sidebar_widget)
        
        # Set initial sizes
        splitter.setSizes([800, 400])
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Create toolbar
        self._setup_toolbar()
        
        # Create status bar
        self.statusBar().showMessage("Ready")
    
    def _setup_toolbar(self):
        """Set up the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(32, 32))
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._on_settings_clicked)
        toolbar.addAction(settings_action)
        
        # Tools action
        tools_action = QAction("Tools", self)
        tools_action.triggered.connect(self._on_tools_clicked)
        toolbar.addAction(tools_action)
        
        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self._on_about_clicked)
        toolbar.addAction(about_action)
        
        self.addToolBar(toolbar)
    
    def _on_send_clicked(self):
        """Handle send button click"""
        message = self.message_input.toPlainText().strip()
        if not message:
            return
        
        # Display user message
        self.display_user_message(message)
        
        # Clear input
        self.message_input.clear()
        
        # Emit signal
        self.message_submitted.emit(message)
    
    def _on_settings_clicked(self):
        """Handle settings button click"""
        QMessageBox.information(self, "Settings", "Settings dialog would appear here")
    
    def _on_tools_clicked(self):
        """Handle tools button click"""
        QMessageBox.information(self, "Tools", "Tools menu would appear here")
    
    def _on_about_clicked(self):
        """Handle about button click"""
        QMessageBox.about(self, "About CPAS Desktop", 
                         "CPAS Desktop v3\nCognitive Processing Automation System\n\n"
                         "A local-first personal assistant system")
    
    def display_user_message(self, message: str):
        """
        Display a user message in the chat
        
        Args:
            message (str): The message to display
        """
        self.chat_display.append(f"<b>You:</b> {message}")
        
        # Scroll to bottom
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
    
    def display_assistant_message(self, message: str):
        """
        Display an assistant message in the chat
        
        Args:
            message (str): The message to display
        """
        self.chat_display.append(f"<b>CPAS:</b> {message}")
        
        # Scroll to bottom
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
    
    def display_system_message(self, message: str):
        """
        Display a system message in the chat
        
        Args:
            message (str): The message to display
        """
        self.chat_display.append(f"<i>System: {message}</i>")
        
        # Scroll to bottom
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
    
    def set_status(self, message: str):
        """
        Set the status bar message
        
        Args:
            message (str): The message to display
        """
        self.statusBar().showMessage(message)
