import logging
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QSplitter, QDialog, QFormLayout,
    QMessageBox
)
from PyQt6.QtCore import pyqtSlot, Qt, QObject # Import QObject for type hint if needed
from typing import Optional # Import Optional

# Import backend types for type hinting
try:
    from ..agent.agent_manager import AgentManager
    from ..utils.config_manager import ConfigManager
    from ..agent.models import AgentStatus, AgentTask # Import AgentTask
except ImportError:
    logging.warning("Could not import backend classes for type hinting in MainWindow.")
    AgentManager = object
    ConfigManager = object
    AgentStatus = object
    AgentTask = object # Dummy type

# Import the shared signal emitter
from .signal_emitter import signal_emitter

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, agent_manager: AgentManager, config_manager: ConfigManager):
        super().__init__()
        logger.info("Initializing MainWindow...")
        self.agent_manager = agent_manager
        self.config_manager = config_manager
        self.selected_agent_id: Optional[str] = None # Track selected agent

        self.setWindowTitle("CPAS v3")
        self.setGeometry(100, 100, 1200, 800)

        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)

        self._layout = QVBoxLayout(self._central_widget)

        # --- Top Bar ---
        self._top_bar_layout = QHBoxLayout()
        self.create_agent_button = QPushButton("Create Agent")
        self.create_agent_button.clicked.connect(self.show_create_agent_dialog)
        self._top_bar_layout.addWidget(self.create_agent_button)
        self._top_bar_layout.addStretch(1)
        self._layout.addLayout(self._top_bar_layout)

        # --- Main Area (Splitter) ---
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._layout.addWidget(self._splitter, 1) # Give splitter more stretch factor

        # --- Left Pane (Agent List) ---
        self._left_pane = QWidget()
        self._left_layout = QVBoxLayout(self._left_pane)
        self._left_layout.addWidget(QLabel("Agents"))
        self.agent_list_widget = QListWidget()
        self.agent_list_widget.currentItemChanged.connect(self.on_agent_selected)
        self._left_layout.addWidget(self.agent_list_widget)
        self._splitter.addWidget(self._left_pane)

        # --- Right Pane (Agent Details/Chat/Log) ---
        self._right_pane = QWidget()
        self._right_layout = QVBoxLayout(self._right_pane)
        self._right_layout.addWidget(QLabel("Agent History / Output"))
        self.agent_details_area = QTextEdit() # History / Output display
        self.agent_details_area.setReadOnly(True)
        self._right_layout.addWidget(self.agent_details_area, 1) # Give stretch

        # --- Task Input Area (Bottom of Right Pane) ---
        self._task_input_layout = QHBoxLayout()
        self.task_input_field = QLineEdit()
        self.task_input_field.setPlaceholderText("Enter task for selected agent...")
        self.submit_task_button = QPushButton("Submit Task")
        self.submit_task_button.clicked.connect(self.submit_task)
        self._task_input_layout.addWidget(self.task_input_field)
        self._task_input_layout.addWidget(self.submit_task_button)
        self._right_layout.addLayout(self._task_input_layout)
        self._splitter.addWidget(self._right_pane)

        # Adjust splitter sizes
        self._splitter.setSizes([250, 950])

        # Initial state: disable task input until agent selected
        self.task_input_field.setEnabled(False)
        self.submit_task_button.setEnabled(False)

        self._connect_signals()
        self._load_initial_data()

        logger.info("MainWindow setup complete.")

    def _connect_signals(self):
        """Connect signals from the signal_emitter to slots in this window."""
        try:
            signal_emitter.agent_created.connect(self.handle_agent_created)
            signal_emitter.agent_removed.connect(self.handle_agent_removed)
            signal_emitter.agent_status_updated.connect(self.update_agent_status)
            signal_emitter.agent_task_updated.connect(self.update_agent_task)
            signal_emitter.agent_history_updated.connect(self.append_history)
            # *** UNCOMMENTED this line ***
            signal_emitter.task_created.connect(self.handle_task_created)
            # signal_emitter.task_queue_updated.connect(self.update_task_queue) # Keep commented for now
            # signal_emitter.resource_usage_updated.connect(self.update_resource_usage) # Keep commented for now
            logger.info("Backend signals connected to MainWindow slots.")
        except Exception as e:
            logger.error(f"Error connecting signals in MainWindow: {e}", exc_info=True)
            QMessageBox.critical(self, "Signal Connection Error", f"Failed to connect UI signals: {e}")

    def _load_initial_data(self):
        """Load initial agent list from the AgentManager."""
        logger.debug("Loading initial agent list...")
        try:
            agents = self.agent_manager.get_all_agents()
            self.agent_list_widget.clear()
            for agent in agents:
                 self._add_agent_to_list(agent.id, agent.name, agent.status)
            logger.info(f"Loaded {len(agents)} agents into list.")
        except Exception as e:
            logger.error(f"Failed to load initial agent list: {e}", exc_info=True)
            QMessageBox.warning(self, "Load Error", f"Failed to load initial agent list: {e}")

    def _add_agent_to_list(self, agent_id: str, agent_name: str, agent_status: AgentStatus):
        """Adds or updates an agent item in the list widget."""
        items = self.agent_list_widget.findItems(f"({agent_id[:8]})", Qt.MatchFlag.MatchContains)
        status_name = agent_status.name if hasattr(agent_status, 'name') else str(agent_status).upper()
        display_text = f"{agent_name} ({agent_id[:8]}) - {status_name}"

        if items:
             item = items[0]
             item.setText(display_text)
             if item.data(Qt.ItemDataRole.UserRole) != agent_id:
                 item.setData(Qt.ItemDataRole.UserRole, agent_id)
        else:
             item = QListWidgetItem(display_text)
             item.setData(Qt.ItemDataRole.UserRole, agent_id)
             self.agent_list_widget.addItem(item)


    # --- Agent Selection ---
    @pyqtSlot(QListWidgetItem, QListWidgetItem)
    def on_agent_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Handles the selection change in the agent list."""
        if current:
            agent_id = current.data(Qt.ItemDataRole.UserRole)
            if agent_id:
                self.selected_agent_id = agent_id
                logger.info(f"Agent selected: {current.text()}")
                self.agent_details_area.clear()
                # TODO (Optional): Load existing history
                self.task_input_field.setEnabled(True)
                self.submit_task_button.setEnabled(True)
            else:
                logger.warning("Selected list item has no agent ID data.")
                self.selected_agent_id = None
                self.agent_details_area.clear()
                self.agent_details_area.setPlaceholderText("Select an agent to see details.")
                self.task_input_field.setEnabled(False)
                self.submit_task_button.setEnabled(False)
        else:
            self.selected_agent_id = None
            self.agent_details_area.clear()
            self.agent_details_area.setPlaceholderText("Select an agent to see details.")
            self.task_input_field.setEnabled(False)
            self.submit_task_button.setEnabled(False)


    # --- Task Submission ---
    @pyqtSlot()
    def submit_task(self):
        """Creates and assigns a task to the selected agent."""
        if not self.selected_agent_id:
            QMessageBox.warning(self, "No Agent Selected", "Please select an agent from the list first.")
            return

        task_description = self.task_input_field.text().strip()
        if not task_description:
            QMessageBox.warning(self, "Empty Task", "Please enter a task description.")
            return

        logger.info(f"Submitting task '{task_description}' for agent {self.selected_agent_id[:8]}")

        try:
             task = AgentTask(description=task_description)
             success = self.agent_manager.assign_task(task)

             if success:
                  self.task_input_field.clear()
             else:
                  QMessageBox.critical(self, "Task Error", "Failed to add task to the queue (manager returned False).")

        except Exception as e:
             logger.error(f"Error submitting task for agent {self.selected_agent_id[:8]}: {e}", exc_info=True)
             QMessageBox.critical(self, "Task Submission Error", f"Failed to submit task:\n{e}")


    # --- Agent Creation Dialog ---
    def show_create_agent_dialog(self):
        """Shows a dialog to get the new agent's name."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Agent")
        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        layout.addRow("Agent Name:", name_input)

        button_box = QHBoxLayout()
        ok_button = QPushButton("Create")
        cancel_button = QPushButton("Cancel")
        button_box.addStretch()
        button_box.addWidget(cancel_button)
        button_box.addWidget(ok_button)
        layout.addRow(button_box)

        ok_button.clicked.connect(lambda checked=False, name=name_input: self.accept_create_agent(dialog, name.text()))
        cancel_button.clicked.connect(dialog.reject)

        dialog.setLayout(layout)
        dialog.exec()

    def accept_create_agent(self, dialog: QDialog, name: str):
        """Handles the creation request from the dialog."""
        if not name or not name.strip():
            QMessageBox.warning(dialog, "Input Error", "Agent name cannot be empty.")
            return

        name = name.strip()
        logger.info(f"Requesting creation of agent with name: '{name}'")
        try:
            new_agent = self.agent_manager.create_agent(name=name)
            if new_agent:
                logger.info(f"Agent '{new_agent.name}' created successfully by manager.")
            else:
                 logger.error("Agent manager returned None when creating agent.")
                 QMessageBox.critical(dialog, "Creation Failed", "Failed to create agent (manager returned None).")

            dialog.accept()
        except Exception as e:
            logger.error(f"Error creating agent '{name}': {e}", exc_info=True)
            QMessageBox.critical(dialog, "Creation Failed", f"Failed to create agent:\n{e}")

    # --- Slots for Backend Signals ---

    @pyqtSlot(dict)
    def handle_agent_created(self, agent_state_dict: dict):
        """Handles the agent_created signal."""
        agent_id = agent_state_dict.get('id')
        agent_name = agent_state_dict.get('name')
        status_str = agent_state_dict.get('status', 'UNKNOWN')
        try:
             agent_status = AgentStatus[status_str.upper()]
        except (KeyError, AttributeError):
             agent_status = AgentStatus.UNKNOWN

        if agent_id and agent_name:
             logger.info(f"[UI SLOT] Agent Created: {agent_name} (ID: {agent_id[:8]}) Status: {agent_status.name}")
             self._add_agent_to_list(agent_id, agent_name, agent_status)
        else:
             logger.error(f"[UI SLOT] Received incomplete agent_created signal: {agent_state_dict}")


    @pyqtSlot(str)
    def handle_agent_removed(self, agent_id: str):
        """Handles the agent_removed signal."""
        logger.info(f"[UI SLOT] Agent Removed: {agent_id[:8]}")
        items = self.agent_list_widget.findItems(f"({agent_id[:8]})", Qt.MatchFlag.MatchContains)
        for item in items:
            if item.data(Qt.ItemDataRole.UserRole) == agent_id:
                 row = self.agent_list_widget.row(item)
                 self.agent_list_widget.takeItem(row)
                 if self.selected_agent_id == agent_id:
                      self.selected_agent_id = None
                      self.agent_details_area.clear()
                      self.agent_details_area.setPlaceholderText("Select an agent to see details.")
                      self.task_input_field.setEnabled(False)
                      self.submit_task_button.setEnabled(False)
                 break


    @pyqtSlot(str, AgentStatus)
    def update_agent_status(self, agent_id: str, status: AgentStatus):
        """Handles the agent_status_updated signal."""
        status_name = status.name if hasattr(status, 'name') else str(status).upper()
        logger.info(f"[UI SLOT] Agent Status Update: {agent_id[:8]} -> {status_name}")
        items = self.agent_list_widget.findItems(f"({agent_id[:8]})", Qt.MatchFlag.MatchContains)
        for item in items:
            if item.data(Qt.ItemDataRole.UserRole) == agent_id:
                 current_text = item.text()
                 parts = current_text.split(' - ')
                 if len(parts) > 0:
                      item.setText(f"{parts[0]} - {status_name}")
                 break


    @pyqtSlot(str, dict)
    def update_agent_task(self, agent_id: str, task_dict: dict):
        """Handles the agent_task_updated signal (placeholder)."""
        task_id = task_dict.get('task_id', 'N/A')
        task_status = task_dict.get('status', 'UNKNOWN')
        logger.info(f"[UI SLOT] Agent Task Update: {agent_id[:8]} - Task {task_id[:8]} -> {task_status}")


    @pyqtSlot(str, dict)
    def append_history(self, agent_id: str, history_entry: dict):
        """Handles the agent_history_updated signal."""
        if agent_id == self.selected_agent_id:
            entry_type = history_entry.get('type', 'message')
            content = history_entry.get('content', '')
            timestamp = history_entry.get('timestamp', '')
            logger.info(f"[UI SLOT] Agent History Update for selected agent: {agent_id[:8]} - Type: {entry_type}")

            self.agent_details_area.append(f"--- {timestamp} [{entry_type.upper()}] ---")
            self.agent_details_area.append(content)
            self.agent_details_area.append("")
        else:
             logger.debug(f"[UI SLOT] Ignoring history update for non-selected agent: {agent_id[:8]}")

    # *** ADDED this missing slot method ***
    @pyqtSlot(dict)
    def handle_task_created(self, task_dict: dict):
        """Handles the task_created signal (placeholder)."""
        task_id = task_dict.get('task_id', 'N/A')
        desc = task_dict.get('description', 'No description')
        logger.info(f"[UI SLOT] Global Task Created: {task_id[:8]} - '{desc[:50]}...'")
        # This slot currently just logs. Could update a global task queue view later.


    # --- Overrides ---
    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Close event triggered on MainWindow.")
        event.accept()
