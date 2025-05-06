"""
Memory Browser for CPAS3
Provides a UI for browsing and searching MongoDB-stored memory
"""
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton, QLineEdit,
    QComboBox, QDateEdit, QSplitter, QTabWidget, QTextEdit, QHeaderView,
    QMessageBox, QCheckBox  # Added QCheckBox import here
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QObject
from PyQt6.QtGui import QIcon

# MongoDB imports
from pymongo import MongoClient

logger = logging.getLogger(__name__)

class MemoryBrowser(QMainWindow):
    """UI for browsing MongoDB-based memory"""
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/", 
                db_name: str = "cpas3_memory"):
        super().__init__()
        
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        
        # Initialize database connection
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client[db_name]
            self.connection_status = True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.connection_status = False
        
        # Set up UI
        self.setWindowTitle("CPAS3 Memory Browser")
        self.resize(1000, 700)
        self.setup_ui()
        
        # Load initial data
        if self.connection_status:
            self.load_recent_interactions()
    
    def setup_ui(self):
        """Set up the user interface"""
        # Create main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Connection status indicator
        status_layout = QHBoxLayout()
        status_label = QLabel("Connection Status:")
        self.status_indicator = QLabel()
        self.update_status_indicator()
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_indicator)
        status_layout.addStretch()
        
        # Add search controls
        search_layout = QHBoxLayout()
        
        # Collection selector
        collection_label = QLabel("Collection:")
        self.collection_selector = QComboBox()
        self.collection_selector.addItems([
            "user_interactions", 
            "agent_responses", 
            "system_events", 
            "errors", 
            "insights"
        ])
        self.collection_selector.currentTextChanged.connect(self.refresh_view)
        
        # Search field
        search_label = QLabel("Search:")
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Enter search terms...")
        self.search_field.returnPressed.connect(self.search_memory)
        
        # Date filter
        date_label = QLabel("Date:")
        self.date_selector = QDateEdit()
        self.date_selector.setCalendarPopup(True)
        self.date_selector.setDate(QDate.currentDate())
        self.date_selector.dateChanged.connect(self.search_memory)
        
        # Date filter checkbox
        self.use_date_filter = QCheckBox("Filter by date")
        self.use_date_filter.setChecked(False)
        self.use_date_filter.stateChanged.connect(self.toggle_date_filter)
        
        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_memory)
        
        # Add widgets to search layout
        search_layout.addWidget(collection_label)
        search_layout.addWidget(self.collection_selector)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_field)
        search_layout.addWidget(date_label)
        search_layout.addWidget(self.date_selector)
        search_layout.addWidget(self.use_date_filter)
        search_layout.addWidget(self.search_button)
        
        # Create tab widget for different views
        self.tab_widget = QTabWidget()
        
        # Table view tab
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        
        # Create table for results
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)  # Adjust based on collection schema
        self.results_table.setHorizontalHeaderLabels(["ID", "Timestamp", "Content", "Type"])
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.selectionModel().selectionChanged.connect(self.show_selected_item)
        
        table_layout.addWidget(self.results_table)
        
        # Detail view tab
        detail_tab = QWidget()
        detail_layout = QVBoxLayout(detail_tab)
        
        # Create detail text view
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        
        detail_layout.addWidget(self.detail_view)
        
        # Add tabs to tab widget
        self.tab_widget.addTab(table_tab, "Table View")
        self.tab_widget.addTab(detail_tab, "Detail View")
        
        # Status bar for results count
        self.results_label = QLabel("No results")
        
        # Add components to main layout
        main_layout.addLayout(status_layout)
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.tab_widget, 1)
        main_layout.addWidget(self.results_label)
        
        # Set central widget
        self.setCentralWidget(central_widget)
    
    def update_status_indicator(self):
        """Update the connection status indicator"""
        if self.connection_status:
            self.status_indicator.setText("Connected to MongoDB")
            self.status_indicator.setStyleSheet("color: green;")
        else:
            self.status_indicator.setText("Not Connected")
            self.status_indicator.setStyleSheet("color: red;")
    
    def load_recent_interactions(self, limit: int = 100):
        """Load recent interactions from the selected collection"""
        if not self.connection_status:
            return
        
        collection_name = self.collection_selector.currentText()
        collection = self.db[collection_name]
        
        try:
            # Get recent documents sorted by timestamp
            cursor = collection.find().sort("timestamp", -1).limit(limit)
            documents = list(cursor)
            
            # Clear existing table
            self.results_table.setRowCount(0)
            
            # Populate table with documents
            for i, doc in enumerate(documents):
                self.results_table.insertRow(i)
                
                # ID cell
                id_item = QTableWidgetItem(str(doc.get("_id", "")))
                self.results_table.setItem(i, 0, id_item)
                
                # Timestamp cell
                timestamp = doc.get("timestamp", "")
                timestamp_item = QTableWidgetItem(timestamp)
                self.results_table.setItem(i, 1, timestamp_item)
                
                # Content cell (adapt based on collection schema)
                content = ""
                if collection_name == "user_interactions":
                    content = doc.get("input_text", "")
                elif collection_name == "agent_responses":
                    content = doc.get("response_text", "")
                elif collection_name == "system_events":
                    content = doc.get("description", "")
                elif collection_name == "errors":
                    content = doc.get("error_message", "")
                elif collection_name == "insights":
                    content = doc.get("content", "")
                
                content_item = QTableWidgetItem(content)
                self.results_table.setItem(i, 2, content_item)
                
                # Type cell (adapt based on collection schema)
                type_value = ""
                if collection_name == "agent_responses":
                    type_value = doc.get("agent_type", "")
                elif collection_name == "system_events":
                    type_value = doc.get("event_type", "")
                elif collection_name == "insights":
                    type_value = doc.get("insight_type", "")
                
                type_item = QTableWidgetItem(type_value)
                self.results_table.setItem(i, 3, type_item)
            
            # Update results label
            self.results_label.setText(f"Showing {len(documents)} results")
            
        except Exception as e:
            logger.error(f"Error loading documents: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load documents: {str(e)}")
    
    def refresh_view(self):
        """Refresh the current view"""
        self.load_recent_interactions()
    
    def search_memory(self):
        """Search memory based on current filters"""
        if not self.connection_status:
            return
        
        collection_name = self.collection_selector.currentText()
        collection = self.db[collection_name]
        search_text = self.search_field.text().strip()
        
        try:
            # Build query
            query = {}
            
            # Add text search if provided
            if search_text:
                # Different fields to search based on collection
                if collection_name == "user_interactions":
                    query["input_text"] = {"$regex": search_text, "$options": "i"}
                elif collection_name == "agent_responses":
                    query["response_text"] = {"$regex": search_text, "$options": "i"}
                elif collection_name == "system_events":
                    query["description"] = {"$regex": search_text, "$options": "i"}
                elif collection_name == "errors":
                    query["error_message"] = {"$regex": search_text, "$options": "i"}
                elif collection_name == "insights":
                    query["content"] = {"$regex": search_text, "$options": "i"}
            
            # Add date filter if enabled
            if self.use_date_filter.isChecked():
                selected_date = self.date_selector.date().toString("yyyy-MM-dd")
                # Simple date filter using string prefix matching
                # A more robust solution would parse dates properly
                query["timestamp"] = {"$regex": f"^{selected_date}"}
            
            # Execute query
            cursor = collection.find(query).sort("timestamp", -1).limit(100)
            documents = list(cursor)
            
            # Clear existing table
            self.results_table.setRowCount(0)
            
            # Populate table with documents
            for i, doc in enumerate(documents):
                self.results_table.insertRow(i)
                
                # ID cell
                id_item = QTableWidgetItem(str(doc.get("_id", "")))
                self.results_table.setItem(i, 0, id_item)
                
                # Timestamp cell
                timestamp = doc.get("timestamp", "")
                timestamp_item = QTableWidgetItem(timestamp)
                self.results_table.setItem(i, 1, timestamp_item)
                
                # Content cell (adapt based on collection schema)
                content = ""
                if collection_name == "user_interactions":
                    content = doc.get("input_text", "")
                elif collection_name == "agent_responses":
                    content = doc.get("response_text", "")
                elif collection_name == "system_events":
                    content = doc.get("description", "")
                elif collection_name == "errors":
                    content = doc.get("error_message", "")
                elif collection_name == "insights":
                    content = doc.get("content", "")
                
                content_item = QTableWidgetItem(content)
                self.results_table.setItem(i, 2, content_item)
                
                # Type cell (adapt based on collection schema)
                type_value = ""
                if collection_name == "agent_responses":
                    type_value = doc.get("agent_type", "")
                elif collection_name == "system_events":
                    type_value = doc.get("event_type", "")
                elif collection_name == "insights":
                    type_value = doc.get("insight_type", "")
                
                type_item = QTableWidgetItem(type_value)
                self.results_table.setItem(i, 3, type_item)
            
            # Update results label
            self.results_label.setText(f"Showing {len(documents)} results")
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            QMessageBox.warning(self, "Error", f"Failed to search documents: {str(e)}")
    
    def show_selected_item(self):
        """Show the selected item in the detail view"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        
        if not selected_rows:
            return
        
        # Get the ID of the selected row
        row_index = selected_rows[0].row()
        doc_id = self.results_table.item(row_index, 0).text()
        
        if not doc_id:
            return
        
        # Get the collection
        collection_name = self.collection_selector.currentText()
        collection = self.db[collection_name]
        
        try:
            # Convert string ID to ObjectId
            from bson.objectid import ObjectId
            doc = collection.find_one({"_id": ObjectId(doc_id)})
            
            if not doc:
                self.detail_view.setText("Document not found")
                return
            
            # Format the document as JSON for display
            import json
            # Convert ObjectId to string for JSON serialization
            doc_copy = dict(doc)
            doc_copy["_id"] = str(doc_copy["_id"])
            formatted_json = json.dumps(doc_copy, indent=2)
            
            self.detail_view.setText(formatted_json)
            
            # Switch to detail view tab
            self.tab_widget.setCurrentIndex(1)
            
        except Exception as e:
            logger.error(f"Error showing document details: {e}")
            self.detail_view.setText(f"Error loading document: {str(e)}")
    
    def toggle_date_filter(self, state):
        """Toggle the date filter on/off"""
        self.date_selector.setEnabled(state)
    
    def closeEvent(self, event):
        """Clean up resources when closing the window"""
        if hasattr(self, 'client'):
            self.client.close()
        event.accept()


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = MemoryBrowser()
    browser.show()
    sys.exit(app.exec())
