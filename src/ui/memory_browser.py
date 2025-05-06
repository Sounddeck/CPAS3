"""
Memory Browser for CPAS3
Allows browsing and searching through stored conversation memories
"""
import logging
from typing import Dict, Any, List, Optional
import datetime

# Qt imports
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox,
    QDateEdit, QDialog, QTextEdit, QSplitter, QGroupBox,
    QHeaderView, QTabWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

# MongoDB imports
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

class MemoryBrowser(QDialog):
    """Dialog for browsing memory entries"""
    
    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        db_name: str = "cpas3_memory",
        parent=None
    ):
        """
        Initialize the memory browser
        
        Args:
            mongo_uri (str): MongoDB connection URI
            db_name (str): Database name
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set window properties
        self.setWindowTitle("CPAS3 Memory Browser")
        self.resize(1000, 600)
        
        # Store settings
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        
        # Initialize MongoDB connection
        self.init_mongo_connection()
        
        # Set up UI
        self.init_ui()
        
        # Load initial data
        self.load_data()
    
    def init_mongo_connection(self):
        """Initialize MongoDB connection"""
        try:
            # Connect to MongoDB
            self.client = MongoClient(self.mongo_uri)
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database reference
            self.db = self.client[self.db_name]
            
            # Get collection references
            self.user_inputs_collection = self.db["user_inputs"]
            self.agent_responses_collection = self.db["agent_responses"]
            self.errors_collection = self.db["errors"]
            self.memory_collection = self.db["agent_chat_history"]
            
            logger.info(f"Connected to MongoDB at {self.mongo_uri}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
            self.connection_error = str(e)
    
    def init_ui(self):
        """Initialize the user interface"""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create tab widget for different memory types
        self.tabs = QTabWidget()
        
        # Create tabs for different memory types
        self.create_user_inputs_tab()
        self.create_agent_responses_tab()
        self.create_errors_tab()
        self.create_memory_tab()
        
        # Add tabs to tab widget
        self.tabs.addTab(self.user_inputs_tab, "User Inputs")
        self.tabs.addTab(self.agent_responses_tab, "Agent Responses")
        self.tabs.addTab(self.errors_tab, "Errors")
        self.tabs.addTab(self.memory_tab, "Chat History")
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tabs)
        
        # Create control buttons
        button_layout = QHBoxLayout()
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_data)
        
        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        
        # Add buttons to layout
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)
    
    def create_user_inputs_tab(self):
        """Create the user inputs tab"""
        self.user_inputs_tab = QWidget()
        layout = QVBoxLayout(self.user_inputs_tab)
        
        # Create search controls
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.user_inputs_search = QLineEdit()
        self.user_inputs_search.setPlaceholderText("Search user inputs...")
        self.user_inputs_search.returnPressed.connect(lambda: self.load_data(tab="user_inputs"))
        
        search_button = QPushButton("Search")
        search_button.clicked.connect(lambda: self.load_data(tab="user_inputs"))
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.user_inputs_search, 1)
        search_layout.addWidget(search_button)
        
        # Create table for user inputs
        self.user_inputs_table = QTableWidget()
        self.user_inputs_table.setColumnCount(4)
        self.user_inputs_table.setHorizontalHeaderLabels(["Timestamp", "Session ID", "Query", "Details"])
        self.user_inputs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.user_inputs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Add widgets to layout
        layout.addLayout(search_layout)
        layout.addWidget(self.user_inputs_table, 1)
    
    def create_agent_responses_tab(self):
        """Create the agent responses tab"""
        self.agent_responses_tab = QWidget()
        layout = QVBoxLayout(self.agent_responses_tab)
        
        # Create search controls
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.agent_responses_search = QLineEdit()
        self.agent_responses_search.setPlaceholderText("Search agent responses...")
        self.agent_responses_search.returnPressed.connect(lambda: self.load_data(tab="agent_responses"))
        
        search_button = QPushButton("Search")
        search_button.clicked.connect(lambda: self.load_data(tab="agent_responses"))
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.agent_responses_search, 1)
        search_layout.addWidget(search_button)
        
        # Create table for agent responses
        self.agent_responses_table = QTableWidget()
        self.agent_responses_table.setColumnCount(5)
        self.agent_responses_table.setHorizontalHeaderLabels(["Timestamp", "Session ID", "Agent Type", "Query", "Response"])
        self.agent_responses_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.agent_responses_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Add widgets to layout
        layout.addLayout(search_layout)
        layout.addWidget(self.agent_responses_table, 1)
    
    def create_errors_tab(self):
        """Create the errors tab"""
        self.errors_tab = QWidget()
        layout = QVBoxLayout(self.errors_tab)
        
        # Create search controls
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.errors_search = QLineEdit()
        self.errors_search.setPlaceholderText("Search errors...")
        self.errors_search.returnPressed.connect(lambda: self.load_data(tab="errors"))
        
        search_button = QPushButton("Search")
        search_button.clicked.connect(lambda: self.load_data(tab="errors"))
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.errors_search, 1)
        search_layout.addWidget(search_button)
        
        # Create table for errors
        self.errors_table = QTableWidget()
        self.errors_table.setColumnCount(4)
        self.errors_table.setHorizontalHeaderLabels(["Timestamp", "Session ID", "Error Message", "Query"])
        self.errors_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.errors_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Add widgets to layout
        layout.addLayout(search_layout)
        layout.addWidget(self.errors_table, 1)
    
    def create_memory_tab(self):
        """Create the memory tab"""
        self.memory_tab = QWidget()
        layout = QVBoxLayout(self.memory_tab)
        
        # Create search controls
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.memory_search = QLineEdit()
        self.memory_search.setPlaceholderText("Search chat history...")
        self.memory_search.returnPressed.connect(lambda: self.load_data(tab="memory"))
        
        search_button = QPushButton("Search")
        search_button.clicked.connect(lambda: self.load_data(tab="memory"))
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.memory_search, 1)
        search_layout.addWidget(search_button)
        
        # Create table for memory entries
        self.memory_table = QTableWidget()
        self.memory_table.setColumnCount(4)
        self.memory_table.setHorizontalHeaderLabels(["Timestamp", "Session ID", "Type", "Content"])
        self.memory_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.memory_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Add widgets to layout
        layout.addLayout(search_layout)
        layout.addWidget(self.memory_table, 1)
    
    def load_data(self, tab=None):
        """
        Load data for the selected tab or all tabs
        
        Args:
            tab (str, optional): Specific tab to load data for
        """
        try:
            # If no specific tab, load data for the current tab
            if tab is None:
                current_tab = self.tabs.currentWidget()
                if current_tab == self.user_inputs_tab:
                    self.load_user_inputs()
                elif current_tab == self.agent_responses_tab:
                    self.load_agent_responses()
                elif current_tab == self.errors_tab:
                    self.load_errors()
                elif current_tab == self.memory_tab:
                    self.load_memory()
            else:
                # Load data for the specified tab
                if tab == "user_inputs":
                    self.load_user_inputs()
                elif tab == "agent_responses":
                    self.load_agent_responses()
                elif tab == "errors":
                    self.load_errors()
                elif tab == "memory":
                    self.load_memory()
        
        except Exception as e:
            logger.error(f"Error loading data: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
    
    def load_user_inputs(self):
        """Load user inputs data"""
        try:
            # Get search query
            search_query = self.user_inputs_search.text().strip()
            
            # Build query
            query = {}
            if search_query:
                query = {"query": {"$regex": search_query, "$options": "i"}}
            
            # Get data from MongoDB
            cursor = self.user_inputs_collection.find(query).sort("timestamp", -1).limit(100)
            
            # Populate table
            self.user_inputs_table.setRowCount(0)
            
            for row_num, doc in enumerate(cursor):
                self.user_inputs_table.insertRow(row_num)
                
                # Timestamp
                timestamp = QTableWidgetItem(self.format_timestamp(doc.get("timestamp")))
                self.user_inputs_table.setItem(row_num, 0, timestamp)
                
                # Session ID
                session_id = QTableWidgetItem(doc.get("session_id", ""))
                self.user_inputs_table.setItem(row_num, 1, session_id)
                
                # Query
                query_item = QTableWidgetItem(doc.get("query", ""))
                self.user_inputs_table.setItem(row_num, 2, query_item)
                
                # Details button
                details_button = QPushButton("View")
                details_button.clicked.connect(lambda _, doc=doc: self.show_details("User Input", doc))
                self.user_inputs_table.setCellWidget(row_num, 3, details_button)
            
            # Resize columns
            self.user_inputs_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error loading user inputs: {e}", exc_info=True)
            raise
    
    def load_agent_responses(self):
        """Load agent responses data"""
        try:
            # Get search query
            search_query = self.agent_responses_search.text().strip()
            
            # Build query
            query = {}
            if search_query:
                query = {
                    "$or": [
                        {"query": {"$regex": search_query, "$options": "i"}},
                        {"response": {"$regex": search_query, "$options": "i"}}
                    ]
                }
            
            # Get data from MongoDB
            cursor = self.agent_responses_collection.find(query).sort("timestamp", -1).limit(100)
            
            # Populate table
            self.agent_responses_table.setRowCount(0)
            
            for row_num, doc in enumerate(cursor):
                self.agent_responses_table.insertRow(row_num)
                
                # Timestamp
                timestamp = QTableWidgetItem(self.format_timestamp(doc.get("timestamp")))
                self.agent_responses_table.setItem(row_num, 0, timestamp)
                
                # Session ID
                session_id = QTableWidgetItem(doc.get("session_id", ""))
                self.agent_responses_table.setItem(row_num, 1, session_id)
                
                # Agent Type
                agent_type = QTableWidgetItem(doc.get("agent_type", ""))
                self.agent_responses_table.setItem(row_num, 2, agent_type)
                
                # Query
                query_item = QTableWidgetItem(doc.get("query", ""))
                self.agent_responses_table.setItem(row_num, 3, query_item)
                
                # Response (truncated)
                response_text = doc.get("response", "")
                if len(response_text) > 100:
                    response_text = response_text[:100] + "..."
                response_item = QTableWidgetItem(response_text)
                self.agent_responses_table.setItem(row_num, 4, response_item)
            
            # Resize columns
            self.agent_responses_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error loading agent responses: {e}", exc_info=True)
            raise
    
    def load_errors(self):
        """Load errors data"""
        try:
            # Get search query
            search_query = self.errors_search.text().strip()
            
            # Build query
            query = {}
            if search_query:
                query = {
                    "$or": [
                        {"error_message": {"$regex": search_query, "$options": "i"}},
                        {"query": {"$regex": search_query, "$options": "i"}}
                    ]
                }
            
            # Get data from MongoDB
            cursor = self.errors_collection.find(query).sort("timestamp", -1).limit(100)
            
            # Populate table
            self.errors_table.setRowCount(0)
            
            for row_num, doc in enumerate(cursor):
                self.errors_table.insertRow(row_num)
                
                # Timestamp
                timestamp = QTableWidgetItem(self.format_timestamp(doc.get("timestamp")))
                self.errors_table.setItem(row_num, 0, timestamp)
                
                # Session ID
                session_id = QTableWidgetItem(doc.get("session_id", ""))
                self.errors_table.setItem(row_num, 1, session_id)
                
                # Error Message
                error_message = QTableWidgetItem(doc.get("error_message", ""))
                self.errors_table.setItem(row_num, 2, error_message)
                
                # Query
                query_item = QTableWidgetItem(doc.get("query", ""))
                self.errors_table.setItem(row_num, 3, query_item)
            
            # Resize columns
            self.errors_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error loading errors: {e}", exc_info=True)
            raise
    
    def load_memory(self):
        """Load memory entries data"""
        try:
            # Get search query
            search_query = self.memory_search.text().strip()
            
            # Build query
            query = {}
            if search_query:
                query = {"content": {"$regex": search_query, "$options": "i"}}
            
            # Get data from MongoDB
            cursor = self.memory_collection.find(query).sort("created_at", -1).limit(100)
            
            # Populate table
            self.memory_table.setRowCount(0)
            
            for row_num, doc in enumerate(cursor):
                self.memory_table.insertRow(row_num)
                
                # Timestamp
                timestamp = QTableWidgetItem(self.format_timestamp(doc.get("created_at")))
                self.memory_table.setItem(row_num, 0, timestamp)
                
                # Session ID
                session_id = QTableWidgetItem(doc.get("session_id", ""))
                self.memory_table.setItem(row_num, 1, session_id)
                
                # Type
                type_item = QTableWidgetItem(doc.get("type", ""))
                self.memory_table.setItem(row_num, 2, type_item)
                
                # Content (truncated)
                content_text = doc.get("content", "")
                if len(content_text) > 100:
                    content_text = content_text[:100] + "..."
                content_item = QTableWidgetItem(content_text)
                self.memory_table.setItem(row_num, 3, content_item)
            
            # Resize columns
            self.memory_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error loading memory entries: {e}", exc_info=True)
            raise
    
    def show_details(self, title: str, document: Dict[str, Any]):
        """
        Show document details in a dialog
        
        Args:
            title (str): Dialog title
            document (Dict[str, Any]): Document to display
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{title} Details")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Create text display
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        # Format document as text
        text = ""
        for key, value in document.items():
            if key == "_id":
                continue
            
            if key == "timestamp" or key == "created_at":
                value = self.format_timestamp(value)
            
            text += f"<b>{key}:</b> {value}<br>"
        
        text_edit.setHtml(text)
        
        # Add to layout
        layout.addWidget(text_edit)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        dialog.exec()
    
    def format_timestamp(self, timestamp) -> str:
        """
        Format a timestamp for display
        
        Args:
            timestamp: The timestamp to format (can be string, datetime or None)
            
        Returns:
            str: Formatted timestamp string
        """
        if not timestamp:
            return ""
        
        try:
            # Handle different timestamp formats
            if isinstance(timestamp, str):
                # Try ISO format
                try:
                    dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return timestamp
            elif isinstance(timestamp, datetime.datetime):
                return timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return str(timestamp)
        except Exception:
            return str(timestamp)
