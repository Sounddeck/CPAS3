"""
Chat Module for CPAS Desktop
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QComboBox, QLabel, QSplitter, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont

class MessageWidget(QFrame):
    """Widget to display a single message in the chat."""
    
    def __init__(self, content, role="user", parent=None):
        super().__init__(parent)
        self.role = role
        self.content = content
        
        # Set up styling
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        
        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add role label
        role_label = QLabel(role.capitalize())
        role_label.setFont(QFont("", 9, QFont.Weight.Bold))
        layout.addWidget(role_label)
        
        # Add content
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(content_label)
        
        # Set background color based on role
        if role == "user":
            self.setStyleSheet(
                "background-color: #f0f0f0; border-radius: 5px; padding: 5px; color: #000000;"
            )
        elif role == "assistant":
            self.setStyleSheet(
                "background-color: #e6f7ff; border-radius: 5px; padding: 5px; color: #000000;"
            )
        else:
            self.setStyleSheet(
                "background-color: #f5f5f5; border-radius: 5px; padding: 5px; color: #000000;"
            )

class ChatModule(QWidget):
    """Chat module for conversations with AI models"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Splitter for resizable areas
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Chat messages area
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        
        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        # Widget to contain all messages
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(10)
        
        # Add stretch to push messages up
        self.messages_layout.addStretch()
        
        # Set up scroll area
        self.scroll_area.setWidget(self.messages_widget)
        chat_layout.addWidget(self.scroll_area)
        
        # Input area
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Model:")
        self.model_selector = QComboBox()
        
        # Add available models
        self.model_selector.addItems(["Default Model", "GPT-3.5", "Llama2"])
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_selector)
        model_layout.addStretch()
        input_layout.addLayout(model_layout)
        
        # Message input
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.setMinimumHeight(50)
        self.message_input.setMaximumHeight(100)
        input_layout.addWidget(self.message_input)
        
        # Send button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumSize(QSize(80, 30))
        self.send_button.clicked.connect(self.send_message)
        button_layout.addWidget(self.send_button)
        
        input_layout.addLayout(button_layout)
        
        # Add containers to splitter
        splitter.addWidget(chat_container)
        splitter.addWidget(input_container)
        
        # Set initial sizes
        splitter.setSizes([500, 200])
        
        # Add welcome message
        self.add_message_widget(
            "Welcome to CPAS Chat. How can I assist you today?", 
            "assistant"
        )
        
        # Set style for dark mode
        self.setStyleSheet("""
            QWidget {
                background-color: #252526;
                color: #FFFFFF;
            }
            
            QTextEdit {
                background-color: #333333;
                border: 1px solid #3F3F46;
                border-radius: 3px;
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
            
            QComboBox {
                background-color: #333333;
                border: 1px solid #3F3F46;
                border-radius: 3px;
                padding: 2px 5px;
                color: #FFFFFF;
            }
        """)
    
    def send_message(self):
        """Handle sending a message."""
        # Get message text
        message_text = self.message_input.toPlainText().strip()
        if not message_text:
            return
        
        # Clear input field
        self.message_input.clear()
        
        # Get selected model
        model = self.model_selector.currentText()
        
        # Add user message
        self.add_message_widget(message_text, "user")
        
        # Simulate AI response
        QTimer.singleShot(500, lambda: self.add_message_widget(
            f"This is a simulated response from {model}.\n\n"
            f"In a fully implemented system, this would be generated by the actual "
            f"AI model based on your message: '{message_text}'",
            "assistant"
        ))
    
    def add_message_widget(self, content, role):
        """Add a message widget to the chat."""
        # Create message widget
        message_widget = MessageWidget(content, role)
        
        # Insert before the stretch at the end
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, message_widget)
        
        # Make sure the widget is visible
        message_widget.show()
        
        # Schedule scrolling after the layout has been updated
        QTimer.singleShot(50, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        """Scroll the view to the bottom to show the latest message."""
        if self.scroll_area:
            # Get vertical scrollbar
            vbar = self.scroll_area.verticalScrollBar()
            # Scroll to maximum (bottom)
            vbar.setValue(vbar.maximum())
    
    def cleanup(self):
        """Handle cleanup when module is unloaded."""
        # Save conversation history, etc.
        pass
