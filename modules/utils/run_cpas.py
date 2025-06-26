from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QPushButton, QInputDialog, QMessageBox, QTabWidget, QDialog, QLineEdit, QFormLayout,
    QTextEdit, QFileDialog, QProgressBar, QComboBox, QSplitter, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
import sys
import qdarkstyle
import os
import time
from agent_backend import AgentBackend
from tab_backends import (
    OllamaClient, DocumentProcessor, ResearchEngine, 
    AgentZero, ChatResponseHandler, TaskEngine
)

class ChatWorker(QThread):
    """Worker thread for handling chat requests."""
    
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, message, model="mistral:7b"):
        super().__init__()
        self.message = message
        self.model = model
        self.chat_handler = ChatResponseHandler()
        
    def run(self):
        try:
            result = self.chat_handler.get_response(self.message, self.model)
            if result["success"]:
                self.response_ready.emit(result["response"])
            else:
                self.error_occurred.emit(result["response"])
        except Exception as e:
            self.error_occurred.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CPAS3 Application")
        self.agent_backend = AgentBackend()
        self.tab_widget = QTabWidget()  # Create a QTabWidget
        
        # Initialize backend components
        self.chat_worker = None
        self.research_engine = ResearchEngine()
        self.agent_zero = AgentZero()
        self.task_engine = TaskEngine()

        # Add all tabs
        self.add_main_chat_tab()
        self.add_deep_research_tab()
        self.add_document_processing_tab()
        self.add_agents_tab()
        self.add_agent_zero_tab()
        self.add_task_manager_tab()
        self.add_agent_manager_tab()

        # Set the QTabWidget as the central widget
        self.setCentralWidget(self.tab_widget)

    def add_main_chat_tab(self):
        """Adds the Main Chat tab with Ollama integration."""
        chat_tab = QWidget()
        layout = QVBoxLayout(chat_tab)

        # Title
        title = QLabel("Main Chat - Ollama Integration")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555;")
        layout.addWidget(self.chat_display)

        # Input area
        input_layout = QHBoxLayout()
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Enter your message here...")
        self.chat_input.setStyleSheet("background-color: #3b3b3b; color: white; border: 1px solid #555; padding: 5px;")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_chat_message)
        self.send_button.setStyleSheet("background-color: #4CAF50; color: white; border: none; padding: 5px 15px;")
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        # Status indicator
        self.chat_status = QLabel("Status: Ready")
        self.chat_status.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.chat_status)

        self.tab_widget.addTab(chat_tab, "Main Chat")

    def send_chat_message(self):
        """Send a message to Ollama."""
        message = self.chat_input.text().strip()
        if not message:
            return
            
        # Display user message
        self.chat_display.append(f"<b>You:</b> {message}")
        self.chat_input.clear()
        self.chat_status.setText("Status: Processing...")
        self.send_button.setEnabled(False)
        
        # Start worker thread
        self.chat_worker = ChatWorker(message)
        self.chat_worker.response_ready.connect(self.handle_chat_response)
        self.chat_worker.error_occurred.connect(self.handle_chat_error)
        self.chat_worker.start()
    
    def handle_chat_response(self, response):
        """Handle successful chat response."""
        self.chat_display.append(f"<b>Assistant:</b> {response}")
        self.chat_display.append("")  # Add blank line
        self.chat_status.setText("Status: Ready")
        self.send_button.setEnabled(True)
        
    def handle_chat_error(self, error):
        """Handle chat error."""
        self.chat_display.append(f"<b>Error:</b> {error}")
        self.chat_display.append("<i>Tip: Make sure Ollama is running on localhost:11434</i>")
        self.chat_display.append("")
        self.chat_status.setText("Status: Error")
        self.send_button.setEnabled(True)

    def add_deep_research_tab(self):
        """Adds the Deep Research tab with simulated research functionality."""
        research_tab = QWidget()
        layout = QVBoxLayout(research_tab)

        # Title
        title = QLabel("Deep Research")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # Research input
        input_layout = QHBoxLayout()
        self.research_input = QLineEdit()
        self.research_input.setPlaceholderText("Enter research topic...")
        self.research_input.setStyleSheet("background-color: #3b3b3b; color: white; border: 1px solid #555; padding: 5px;")
        
        self.research_button = QPushButton("Start Research")
        self.research_button.clicked.connect(self.start_research)
        self.research_button.setStyleSheet("background-color: #2196F3; color: white; border: none; padding: 5px 15px;")
        
        input_layout.addWidget(self.research_input)
        input_layout.addWidget(self.research_button)
        layout.addLayout(input_layout)

        # Research results area
        self.research_results = QTextEdit()
        self.research_results.setReadOnly(True)
        self.research_results.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555;")
        layout.addWidget(self.research_results)

        # Progress bar
        self.research_progress = QProgressBar()
        self.research_progress.setVisible(False)
        layout.addWidget(self.research_progress)

        self.tab_widget.addTab(research_tab, "Deep Research")

    def start_research(self):
        """Start simulated research process."""
        topic = self.research_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "Input Required", "Please enter a research topic.")
            return

        self.research_results.clear()
        self.research_results.append(f"<b>Research Topic:</b> {topic}")
        self.research_results.append("")
        
        # Simulate research progress
        self.research_progress.setVisible(True)
        self.research_progress.setValue(0)
        self.research_button.setEnabled(False)
        
        # Use the research engine
        research_data = self.research_engine.conduct_research(topic)
        
        self.current_step = 0
        self.research_steps = [(step, (i+1)*20) for i, step in enumerate(research_data["steps"])]
        self.research_data = research_data
        self.research_timer = QTimer()
        self.research_timer.timeout.connect(self.update_research_progress)
        self.research_timer.start(1000)  # Update every second

    def update_research_progress(self):
        """Update research progress simulation."""
        if self.current_step < len(self.research_steps):
            step_text, progress = self.research_steps[self.current_step]
            self.research_results.append(f"• {step_text}")
            self.research_progress.setValue(progress)
            self.current_step += 1
        else:
            # Research complete
            self.research_timer.stop()
            self.research_progress.setVisible(False)
            self.research_button.setEnabled(True)
            
            # Add results from research engine
            self.research_results.append("")
            self.research_results.append("<b>Research Results:</b>")
            for finding in self.research_data["findings"]:
                self.research_results.append(f"• {finding}")
            
            self.research_results.append("")
            self.research_results.append(f"<b>Analysis Confidence:</b> {self.research_data['confidence']}%")
            self.research_results.append(f"<b>Sources Scanned:</b> {self.research_data['sources_scanned']}")
            self.research_results.append(f"<b>Relevant Results:</b> {self.research_data['relevant_results']}")
            self.research_results.append("")
            self.research_results.append("<i>Note: This is a simulated research result. Connect to actual research services for real data.</i>")

    def add_document_processing_tab(self):
        """Adds the Document Processing tab with file handling."""
        doc_tab = QWidget()
        layout = QVBoxLayout(doc_tab)

        # Title
        title = QLabel("Document Processing")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # File selection area
        file_layout = QHBoxLayout()
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("color: #ccc; padding: 5px;")
        
        self.select_file_button = QPushButton("Select File")
        self.select_file_button.clicked.connect(self.select_file)
        self.select_file_button.setStyleSheet("background-color: #FF9800; color: white; border: none; padding: 5px 15px;")
        
        self.process_file_button = QPushButton("Process File")
        self.process_file_button.clicked.connect(self.process_file)
        self.process_file_button.setEnabled(False)
        self.process_file_button.setStyleSheet("background-color: #4CAF50; color: white; border: none; padding: 5px 15px;")
        
        file_layout.addWidget(self.file_path_label)
        file_layout.addWidget(self.select_file_button)
        file_layout.addWidget(self.process_file_button)
        layout.addLayout(file_layout)

        # Processing results area
        self.processing_results = QTextEdit()
        self.processing_results.setReadOnly(True)
        self.processing_results.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555;")
        layout.addWidget(self.processing_results)

        # Supported formats info
        supported_info = QLabel("Supported formats: " + ", ".join(DocumentProcessor.supported_extensions()))
        supported_info.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(supported_info)

        self.tab_widget.addTab(doc_tab, "Document Processing")
        
        # Store selected file path
        self.selected_file_path = None

    def select_file(self):
        """Open file dialog to select a document."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document",
            "",
            "Text Files (*.txt);;Markdown Files (*.md);;Python Files (*.py);;JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            self.file_path_label.setText(f"Selected: {os.path.basename(file_path)}")
            self.process_file_button.setEnabled(True)

    def process_file(self):
        """Process the selected file."""
        if not self.selected_file_path:
            QMessageBox.warning(self, "No File", "Please select a file first.")
            return
            
        self.processing_results.clear()
        self.processing_results.append("Processing file...")
        
        # Process the file
        result = DocumentProcessor.process_text_file(self.selected_file_path)
        self.processing_results.clear()
        self.processing_results.append(result)

    def add_agents_tab(self):
        """Adds the Agents tab with agent functionality."""
        agents_tab = QWidget()
        layout = QVBoxLayout(agents_tab)

        # Title
        title = QLabel("Agents Management")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # Agent creation area
        creation_layout = QHBoxLayout()
        self.agent_name_input = QLineEdit()
        self.agent_name_input.setPlaceholderText("Enter agent name...")
        self.agent_name_input.setStyleSheet("background-color: #3b3b3b; color: white; border: 1px solid #555; padding: 5px;")
        
        self.agent_type_combo = QComboBox()
        self.agent_type_combo.addItems(["Research Agent", "Analysis Agent", "Support Agent", "Custom Agent"])
        self.agent_type_combo.setStyleSheet("background-color: #3b3b3b; color: white; border: 1px solid #555;")
        
        self.create_agent_button = QPushButton("Create Agent")
        self.create_agent_button.clicked.connect(self.create_custom_agent)
        self.create_agent_button.setStyleSheet("background-color: #9C27B0; color: white; border: none; padding: 5px 15px;")
        
        creation_layout.addWidget(QLabel("Name:"))
        creation_layout.addWidget(self.agent_name_input)
        creation_layout.addWidget(QLabel("Type:"))
        creation_layout.addWidget(self.agent_type_combo)
        creation_layout.addWidget(self.create_agent_button)
        layout.addLayout(creation_layout)

        # Agents display area
        self.agents_display = QTextEdit()
        self.agents_display.setReadOnly(True)
        self.agents_display.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555;")
        layout.addWidget(self.agents_display)

        # Load initial agents
        self.refresh_agents_display()

        self.tab_widget.addTab(agents_tab, "Agents")

    def create_custom_agent(self):
        """Create a new custom agent."""
        name = self.agent_name_input.text().strip()
        agent_type = self.agent_type_combo.currentText()
        
        if not name:
            QMessageBox.warning(self, "Input Required", "Please enter an agent name.")
            return
            
        # Add to backend
        new_agent = {
            "id": self.agent_backend.next_id,
            "name": name,
            "status": "Created",
            "task": f"Ready for {agent_type.lower()} tasks",
            "type": agent_type
        }
        
        self.agent_backend.agents.append(new_agent)
        self.agent_backend.next_id += 1
        
        self.agent_name_input.clear()
        self.refresh_agents_display()
        
        QMessageBox.information(self, "Agent Created", f"Agent '{name}' has been created successfully!")

    def refresh_agents_display(self):
        """Refresh the agents display."""
        self.agents_display.clear()
        self.agents_display.append("<b>Active Agents:</b>")
        self.agents_display.append("")
        
        for agent in self.agent_backend.get_agents():
            agent_type = agent.get("type", "Generic Agent")
            self.agents_display.append(f"<b>{agent['name']}</b> ({agent_type})")
            self.agents_display.append(f"  Status: {agent['status']}")
            self.agents_display.append(f"  Task: {agent['task']}")
            self.agents_display.append("")

    def add_agent_zero_tab(self):
        """Adds the Agent Zero tab with advanced agent functionality."""
        agent_zero_tab = QWidget()
        layout = QVBoxLayout(agent_zero_tab)

        # Title
        title = QLabel("Agent Zero - Advanced AI Assistant")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # Command input area
        command_layout = QHBoxLayout()
        self.agent_zero_input = QLineEdit()
        self.agent_zero_input.setPlaceholderText("Enter command for Agent Zero...")
        self.agent_zero_input.setStyleSheet("background-color: #3b3b3b; color: white; border: 1px solid #555; padding: 5px;")
        self.agent_zero_input.returnPressed.connect(self.execute_agent_zero_command)
        
        self.execute_button = QPushButton("Execute")
        self.execute_button.clicked.connect(self.execute_agent_zero_command)
        self.execute_button.setStyleSheet("background-color: #F44336; color: white; border: none; padding: 5px 15px;")
        
        command_layout.addWidget(self.agent_zero_input)
        command_layout.addWidget(self.execute_button)
        layout.addLayout(command_layout)

        # Results area
        self.agent_zero_results = QTextEdit()
        self.agent_zero_results.setReadOnly(True)
        self.agent_zero_results.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555;")
        layout.addWidget(self.agent_zero_results)

        # System status
        status_layout = QHBoxLayout()
        self.agent_zero_status = QLabel("Agent Zero Status: Online")
        self.agent_zero_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        self.clear_results_button = QPushButton("Clear Results")
        self.clear_results_button.clicked.connect(lambda: self.agent_zero_results.clear())
        self.clear_results_button.setStyleSheet("background-color: #666; color: white; border: none; padding: 5px 15px;")
        
        status_layout.addWidget(self.agent_zero_status)
        status_layout.addStretch()
        status_layout.addWidget(self.clear_results_button)
        layout.addLayout(status_layout)

        self.tab_widget.addTab(agent_zero_tab, "Agent Zero")

    def execute_agent_zero_command(self):
        """Execute a command through Agent Zero."""
        command = self.agent_zero_input.text().strip()
        if not command:
            return
            
        self.agent_zero_results.append(f"<b>Command:</b> {command}")
        self.agent_zero_input.clear()
        
        # Use Agent Zero backend
        result = self.agent_zero.execute_command(command)
        self.agent_zero_results.append(f"<b>Response:</b> {result['result']}")
        self.agent_zero_results.append("")

    def add_task_manager_tab(self):
        """Adds the Task Manager tab to the UI."""
        task_manager_tab = QWidget()
        task_layout = QVBoxLayout(task_manager_tab)

        # Add title
        title = QLabel("Task Manager")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: black;")
        task_layout.addWidget(title)

        # Add task table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)  # Task Name, Agent, Priority, Progress, Actions
        self.task_table.setHorizontalHeaderLabels(["Task Name", "Agent", "Priority", "Progress", "Actions"])
        self.task_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # Stretch columns
        self.task_table.verticalHeader().setVisible(False)  # Hide row numbers

        # Populate with backend data
        self.populate_task_table()

        task_layout.addWidget(self.task_table)
        self.tab_widget.addTab(task_manager_tab, "Task Manager")  # Add to QTabWidget

    def populate_task_table(self):
        """Populates the task table with data from the backend."""
        tasks = self.agent_backend.get_tasks()
        agents = {agent["id"]: agent["name"] for agent in self.agent_backend.get_agents()}
        self.task_table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            self.task_table.setItem(row, 0, QTableWidgetItem(task["name"]))
            self.task_table.setItem(row, 1, QTableWidgetItem(agents.get(task["agent_id"], "Unassigned")))
            self.task_table.setItem(row, 2, QTableWidgetItem(task["priority"]))
            self.task_table.setItem(row, 3, QTableWidgetItem(f"{task['progress']}%"))

            # Add action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(5)

            update_button = QPushButton("Update Progress")
            update_priority_button = QPushButton("Update Priority")
            update_button.setFixedSize(120, 30)
            update_priority_button.setFixedSize(120, 30)

            actions_layout.addWidget(update_button)
            actions_layout.addWidget(update_priority_button)
            self.task_table.setCellWidget(row, 4, actions_widget)

    def add_agent_manager_tab(self):
        """Adds the Agent Manager tab to the UI."""
        agent_manager_tab = QWidget()
        agent_layout = QVBoxLayout(agent_manager_tab)

        # Add title
        title = QLabel("Agent Manager")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: black;")
        agent_layout.addWidget(title)

        # Add agent table
        self.agent_table = QTableWidget()
        self.agent_table.setColumnCount(4)  # Name, Status, Task, Actions
        self.agent_table.setHorizontalHeaderLabels(["Name", "Status", "Task", "Actions"])
        self.agent_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.agent_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.agent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # Stretch columns
        self.agent_table.verticalHeader().setVisible(False)  # Hide row numbers

        # Populate with backend data
        self.populate_agent_table()

        agent_layout.addWidget(self.agent_table)

        # Add "Create Agent" button
        create_agent_button = QPushButton("Create Agent")
        create_agent_button.clicked.connect(self.create_agent)
        agent_layout.addWidget(create_agent_button)

        self.tab_widget.addTab(agent_manager_tab, "Agent Manager")  # Add to QTabWidget

    def populate_agent_table(self):
        """Populates the agent table with data from the backend."""
        agents = self.agent_backend.get_agents()
        self.agent_table.setRowCount(len(agents))

        for row, agent in enumerate(agents):
            self.agent_table.setItem(row, 0, QTableWidgetItem(agent["name"]))
            self.agent_table.setItem(row, 1, QTableWidgetItem(agent["status"]))
            self.agent_table.setItem(row, 2, QTableWidgetItem(agent["task"]))

            # Add action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(5)

            start_button = QPushButton("Start")
            stop_button = QPushButton("Stop")
            edit_button = QPushButton("Edit")
            start_button.setFixedSize(80, 30)
            stop_button.setFixedSize(80, 30)
            edit_button.setFixedSize(80, 30)

            start_button.clicked.connect(lambda _, r=row: self.start_agent(r))
            stop_button.clicked.connect(lambda _, r=row: self.stop_agent(r))
            edit_button.clicked.connect(lambda _, r=row: self.edit_agent(r))

            actions_layout.addWidget(start_button)
            actions_layout.addWidget(stop_button)
            actions_layout.addWidget(edit_button)
            self.agent_table.setCellWidget(row, 3, actions_widget)

    def create_agent(self):
        """Creates a new agent."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Agent")
        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        layout.addRow("Name:", name_input)

        def on_create():
            name = name_input.text()
            if name:
                self.agent_backend.agents.append({
                    "id": self.agent_backend.next_id,
                    "name": name,
                    "status": "Stopped",
                    "task": "Idle"
                })
                self.agent_backend.next_id += 1
                self.populate_agent_table()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Error", "Agent name cannot be empty.")

        create_button = QPushButton("Create")
        create_button.clicked.connect(on_create)
        layout.addWidget(create_button)

        dialog.exec()

    def start_agent(self, row):
        """Starts an agent."""
        agent = self.agent_backend.get_agents()[row]
        agent["status"] = "Running"
        self.populate_agent_table()

    def stop_agent(self, row):
        """Stops an agent."""
        agent = self.agent_backend.get_agents()[row]
        agent["status"] = "Stopped"
        self.populate_agent_table()

    def edit_agent(self, row):
        """Edits an agent."""
        agent = self.agent_backend.get_agents()[row]
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Agent")
        layout = QFormLayout(dialog)

        name_input = QLineEdit(agent["name"])
        layout.addRow("Name:", name_input)

        def on_save():
            agent["name"] = name_input.text()
            self.populate_agent_table()
            dialog.accept()

        save_button = QPushButton("Save")
        save_button.clicked.connect(on_save)
        layout.addWidget(save_button)

        dialog.exec()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
