import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QFormLayout, QLineEdit, QTextEdit, QComboBox,
    QDialog, QDialogButtonBox, QMessageBox, QSizePolicy, QGroupBox, QScrollArea,
    QPlainTextEdit, QTreeWidget, QTreeWidgetItem, QHeaderView
)

# Import AgentStatus if needed for display
from .agents.base_agent import AgentStatus

# Use TYPE_CHECKING to avoid circular import issues with AgentManager
if TYPE_CHECKING:
    from .agent_manager import AgentManager
    from .agents.base_agent import Agent # Import Agent for type hinting

logger = logging.getLogger(__name__)

# --- Agent Detail Widget ---
class AgentDetailWidget(QWidget):
    """Displays details and controls for a selected agent."""
    def __init__(self, agent_manager: 'AgentManager', parent=None):
        super().__init__(parent)
        self.agent_manager = agent_manager
        self.current_agent_id: Optional[str] = None
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self.clear_details() # Start empty

    def _create_widgets(self):
        # Agent Info Group
        self.info_group = QGroupBox("Agent Information")
        self.info_layout = QFormLayout()
        self.name_label = QLabel("N/A")
        self.id_label = QLabel("N/A")
        self.type_label = QLabel("N/A")
        self.status_label = QLabel("N/A")
        self.description_edit = QTextEdit()
        self.description_edit.setReadOnly(True)
        self.description_edit.setMaximumHeight(80) # Limit height

        self.info_layout.addRow("Name:", self.name_label)
        self.info_layout.addRow("ID:", self.id_label)
        self.info_layout.addRow("Type:", self.type_label)
        self.info_layout.addRow("Status:", self.status_label)
        self.info_layout.addRow("Description:", self.description_edit)
        self.info_group.setLayout(self.info_layout)

        # Agent Controls Group
        self.controls_group = QGroupBox("Controls")
        self.controls_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.delete_button = QPushButton("Delete Agent")
        self.delete_button.setStyleSheet("color: red;") # Make delete stand out
        self.controls_layout.addWidget(self.start_button)
        self.controls_layout.addWidget(self.stop_button)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.delete_button)
        self.controls_group.setLayout(self.controls_layout)

        # Agent State/Data Display (Using QTreeWidget for structured data)
        self.state_group = QGroupBox("Agent State / Data")
        self.state_layout = QVBoxLayout()
        self.state_tree = QTreeWidget()
        self.state_tree.setColumnCount(2)
        self.state_tree.setHeaderLabels(["Key", "Value"])
        self.state_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.state_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.state_layout.addWidget(self.state_tree)
        self.state_group.setLayout(self.state_layout)

        # Placeholder for future tabs (e.g., Logs, Performance)
        # self.tabs = QTabWidget()
        # self.tabs.addTab(QWidget(), "State") # Replace with state widget
        # self.tabs.addTab(QWidget(), "Logs") # Replace with agent-specific log widget
        # self.tabs.addTab(QWidget(), "Performance") # Replace with performance widget

    def _setup_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.info_group)
        main_layout.addWidget(self.controls_group)
        main_layout.addWidget(self.state_group) # Add state group
        # main_layout.addWidget(self.tabs) # Use tabs if implemented
        main_layout.addStretch() # Push everything up

    def _connect_signals(self):
        self.start_button.clicked.connect(self.start_agent)
        self.stop_button.clicked.connect(self.stop_agent)
        self.delete_button.clicked.connect(self.delete_agent)

    def update_details(self, agent: Optional['Agent']):
        """Update the display with the details of the given agent."""
        if agent:
            self.current_agent_id = agent.id
            self.name_label.setText(agent.name)
            self.id_label.setText(agent.id)
            self.id_label.setToolTip(agent.id) # Show full ID on hover
            self.type_label.setText(getattr(agent, 'type', 'Unknown')) # Use getattr for safety
            self.update_status(agent.status)
            self.description_edit.setText(agent.description or "No description provided.")

            # Update state tree
            self.state_tree.clear()
            try:
                state_data = agent.get_serializable_state()
                self._populate_tree(self.state_tree.invisibleRootItem(), state_data)
                self.state_tree.expandToDepth(0) # Expand top level
            except Exception as e:
                 logger.error(f"Error getting serializable state for agent {agent.id}: {e}")
                 error_item = QTreeWidgetItem(self.state_tree.invisibleRootItem(), ["Error", f"Could not retrieve state: {e}"])
                 error_item.setForeground(0, QtGui.QBrush(QtGui.QColor("red")))
                 error_item.setForeground(1, QtGui.QBrush(QtGui.QColor("red")))


            self.start_button.setEnabled(agent.status in [AgentStatus.IDLE, AgentStatus.STOPPED, AgentStatus.FAILED, AgentStatus.COMPLETED, AgentStatus.INITIALIZING, AgentStatus.ERROR])
            self.stop_button.setEnabled(agent.status in [AgentStatus.RUNNING, AgentStatus.THINKING]) # Enable stop if running or thinking
            self.delete_button.setEnabled(True)
            self.info_group.setEnabled(True)
            self.controls_group.setEnabled(True)
            self.state_group.setEnabled(True)
        else:
            self.clear_details()

    def _populate_tree(self, parent_item: QTreeWidgetItem, data: Any):
        """Recursively populate the QTreeWidget."""
        if isinstance(data, dict):
            for key, value in data.items():
                child_item = QTreeWidgetItem(parent_item, [str(key)])
                self._populate_tree(child_item, value)
        elif isinstance(data, list):
            for index, value in enumerate(data):
                 child_item = QTreeWidgetItem(parent_item, [f"[{index}]"])
                 self._populate_tree(child_item, value)
        else:
            # Set value in the second column of the parent
            parent_item.setText(1, str(data))
            # Optionally truncate long values
            if len(str(data)) > 100:
                 parent_item.setToolTip(1, str(data)) # Show full value on hover
                 parent_item.setText(1, str(data)[:100] + "...")


    def update_status(self, status: AgentStatus):
        """Update the status label and button states based on agent status."""
        self.status_label.setText(status.value)
        # Set color based on status
        color = "black"
        if status in [AgentStatus.RUNNING, AgentStatus.THINKING]:
            color = "green"
        elif status in [AgentStatus.STOPPED, AgentStatus.IDLE, AgentStatus.COMPLETED]:
            color = "gray"
        elif status in [AgentStatus.FAILED, AgentStatus.ERROR]:
            color = "red"
        elif status == AgentStatus.INITIALIZING:
            color = "orange"
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        # Update button enablement based on status
        agent = self.agent_manager.get_agent(self.current_agent_id) if self.current_agent_id else None
        if agent:
             self.start_button.setEnabled(status in [AgentStatus.IDLE, AgentStatus.STOPPED, AgentStatus.FAILED, AgentStatus.COMPLETED, AgentStatus.INITIALIZING, AgentStatus.ERROR])
             self.stop_button.setEnabled(status in [AgentStatus.RUNNING, AgentStatus.THINKING])


    def clear_details(self):
        """Clear all fields when no agent is selected."""
        self.current_agent_id = None
        self.name_label.setText("N/A")
        self.id_label.setText("N/A")
        self.id_label.setToolTip("")
        self.type_label.setText("N/A")
        self.status_label.setText("N/A")
        self.status_label.setStyleSheet("color: black; font-weight: normal;")
        self.description_edit.setText("")
        self.state_tree.clear()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.info_group.setEnabled(False)
        self.controls_group.setEnabled(False)
        self.state_group.setEnabled(False)

    def start_agent(self):
        if self.current_agent_id:
            logger.info(f"UI requesting start for agent {self.current_agent_id}")
            try:
                self.agent_manager.start_agent(self.current_agent_id)
                # Optimistically update status, will be corrected by refresh
                self.update_status(AgentStatus.RUNNING)
            except Exception as e:
                 logger.error(f"Error starting agent {self.current_agent_id} from UI: {e}", exc_info=True)
                 QMessageBox.warning(self, "Start Agent Error", f"Could not start agent:\n{e}")

    def stop_agent(self):
        if self.current_agent_id:
            logger.info(f"UI requesting stop for agent {self.current_agent_id}")
            try:
                self.agent_manager.stop_agent(self.current_agent_id)
                # Optimistically update status, will be corrected by refresh
                self.update_status(AgentStatus.STOPPED)
            except Exception as e:
                 logger.error(f"Error stopping agent {self.current_agent_id} from UI: {e}", exc_info=True)
                 QMessageBox.warning(self, "Stop Agent Error", f"Could not stop agent:\n{e}")

    def delete_agent(self):
        if not self.current_agent_id:
            return

        agent = self.agent_manager.get_agent(self.current_agent_id)
        agent_name = agent.name if agent else self.current_agent_id

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to permanently delete agent '{agent_name}' ({self.current_agent_id})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            logger.info(f"UI requesting deletion for agent {self.current_agent_id}")
            try:
                success = self.agent_manager.delete_agent(self.current_agent_id)
                if success:
                    logger.info(f"Agent {self.current_agent_id} deleted successfully via UI.")
                    self.clear_details()
                    # Signal the parent (AgentWindow) to refresh the list
                    if hasattr(self.parent(), 'refresh_agent_list'):
                         self.parent().refresh_agent_list()
                else:
                    # This case might happen if the agent was already gone
                    logger.warning(f"Agent {self.current_agent_id} could not be deleted (maybe already gone?).")
                    QMessageBox.warning(self, "Delete Agent", "Agent could not be deleted (it might have been removed already).")
                    # Still clear details and refresh list
                    self.clear_details()
                    if hasattr(self.parent(), 'refresh_agent_list'):
                         self.parent().refresh_agent_list()

            except Exception as e:
                 logger.error(f"Error deleting agent {self.current_agent_id} from UI: {e}", exc_info=True)
                 QMessageBox.critical(self, "Delete Agent Error", f"Could not delete agent:\n{e}")


# --- Add Agent Dialog ---
class AddAgentDialog(QDialog):
    """Dialog for creating a new agent."""
    def __init__(self, agent_manager: 'AgentManager', parent=None):
        super().__init__(parent)
        self.agent_manager = agent_manager
        self.setWindowTitle("Add New Agent")

        # Widgets
        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.type_combo = QComboBox()

        # Populate agent types
        # --- Get types dynamically from AgentManager ---
        available_types = ["Generic", "Task"] # Default fallback
        if self.agent_manager and hasattr(self.agent_manager, '_get_agent_class'):
             # Access the internal map keys used by _get_agent_class
             # This is a bit of an internal detail access, might need refinement
             # if AgentManager structure changes significantly.
             try:
                  # Assuming _get_agent_class uses a map like {"TypeName": Class}
                  # Import necessary types here, carefully
                  from .agents.base_agent import Agent
                  from .agents.task_agent import TaskAgent
                  type_map = {
                       "Generic": Agent,
                       "Task": TaskAgent
                       # Add other types here if AgentManager knows them
                  }
                  # Or, if AgentManager has a dedicated method:
                  # available_types = self.agent_manager.get_available_agent_types()
                  available_types = list(type_map.keys())
                  logger.debug(f"Found agent types: {available_types}")
             except ImportError as ie:
                  logger.warning(f"Could not import specific agent types for dialog type map: {ie}")
             except Exception as e:
                  logger.error(f"Error getting agent types for dialog: {e}", exc_info=True)

        self.type_combo.addItems(available_types)
        # --- End dynamic type population ---


        # Layout
        form_layout = QFormLayout()
        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Type:", self.type_combo)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)

    def get_agent_data(self) -> Optional[Dict[str, Any]]:
        """Returns the data entered by the user, or None if invalid."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Information", "Agent name cannot be empty.")
            return None
        return {
            "name": name,
            "description": self.description_edit.toPlainText().strip(),
            "type": self.type_combo.currentText() # Use 'type' key
        }

# --- Main Agent Window Widget ---
class AgentWindow(QWidget):
    """Main widget for managing and viewing agents."""
    def __init__(self, agent_manager: 'AgentManager', parent=None):
        super().__init__(parent)
        if agent_manager is None:
             logger.error("AgentWindow initialized without a valid AgentManager!")
             # Display an error message instead of the normal UI
             error_layout = QVBoxLayout(self)
             error_label = QLabel("Error: Agent Manager is not available. Cannot display agent information.")
             error_label.setAlignment(QtCore.Qt.AlignCenter)
             error_label.setStyleSheet("color: red; font-size: 16px;")
             error_layout.addWidget(error_label)
             return # Stop initialization

        self.agent_manager = agent_manager
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self.refresh_agent_list()

        # Timer for periodic refresh of agent list and statuses
        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_agent_status)
        self.refresh_timer.start(5000) # Refresh every 5 seconds (5000 ms)

    def _create_widgets(self):
        # Agent List
        self.agent_list_widget = QListWidget()
        self.agent_list_widget.setSortingEnabled(True) # Allow sorting by name

        # Add Agent Button
        self.add_agent_button = QPushButton("Add Agent")

        # Agent Detail View
        self.agent_detail_widget = AgentDetailWidget(self.agent_manager, self)

    def _setup_layout(self):
        # Left side (List and Add Button)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Agents:"))
        left_layout.addWidget(self.agent_list_widget)
        left_layout.addWidget(self.add_agent_button)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # Right side (Details) - Already a QWidget
        right_widget = self.agent_detail_widget

        # Splitter
        splitter = QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1) # Give list less initial space
        splitter.setStretchFactor(1, 3) # Give details more initial space
        splitter.setSizes([250, 750]) # Initial size hint

        # Main layout for the AgentWindow widget
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(splitter)

    def _connect_signals(self):
        self.agent_list_widget.currentItemChanged.connect(self.on_agent_selected)
        self.add_agent_button.clicked.connect(self.open_add_agent_dialog)

    def refresh_agent_list(self):
        """Clears and repopulates the agent list from the AgentManager."""
        logger.debug("Refreshing agent list...")
        current_selection_id = self.agent_list_widget.currentItem().data(QtCore.Qt.UserRole) if self.agent_list_widget.currentItem() else None
        selected_item = None

        self.agent_list_widget.clear()
        try:
            agents = self.agent_manager.list_agents()
            logger.debug(f"Found {len(agents)} agents.")
            for agent in sorted(agents, key=lambda a: a.name): # Sort alphabetically by name
                item = QListWidgetItem(f"{agent.name} ({agent.status.value})")
                item.setData(QtCore.Qt.UserRole, agent.id) # Store agent ID
                item.setToolTip(f"ID: {agent.id}\nType: {getattr(agent, 'type', 'Unknown')}")
                # Set icon or color based on status (optional)
                self.agent_list_widget.addItem(item)
                if agent.id == current_selection_id:
                     selected_item = item # Keep track if the previously selected item is re-added

            # Restore selection if the item still exists
            if selected_item:
                 self.agent_list_widget.setCurrentItem(selected_item)
            # If previous selection is gone, clear details
            elif current_selection_id:
                 self.agent_detail_widget.clear_details()


        except Exception as e:
            logger.error(f"Failed to refresh agent list: {e}", exc_info=True)
            # Optionally display an error item in the list
            error_item = QListWidgetItem("Error loading agents!")
            error_item.setForeground(QtGui.QBrush(QtGui.QColor("red")))
            self.agent_list_widget.addItem(error_item)

    def refresh_agent_status(self):
        """Updates the status display in the list and detail view without full list rebuild."""
        logger.debug("Refreshing agent statuses...")
        selected_agent_id = None
        items_to_remove = [] # Collect items to remove after iteration

        for i in range(self.agent_list_widget.count()):
            item = self.agent_list_widget.item(i)
            if not item: continue # Should not happen, but safety check
            agent_id = item.data(QtCore.Qt.UserRole)
            if not agent_id: # Skip non-agent items
                continue

            agent = self.agent_manager.get_agent(agent_id)
            if agent:
                # Update text in list item
                new_text = f"{agent.name} ({agent.status.value})"
                if item.text() != new_text:
                    item.setText(new_text)

                # Update detail view if this agent is selected
                if self.agent_list_widget.currentItem() == item:
                    selected_agent_id = agent_id
                    self.agent_detail_widget.update_status(agent.status)
                    # Also refresh state data periodically if desired
                    try:
                         state_data = agent.get_serializable_state()
                         self.agent_detail_widget.state_tree.clear()
                         self.agent_detail_widget._populate_tree(self.agent_detail_widget.state_tree.invisibleRootItem(), state_data)
                         self.agent_detail_widget.state_tree.expandToDepth(0)
                    except Exception as e:
                         logger.error(f"Error refreshing state for agent {agent.id}: {e}")
                         # Clear tree and show error
                         self.agent_detail_widget.state_tree.clear()
                         error_item_tree = QTreeWidgetItem(self.agent_detail_widget.state_tree.invisibleRootItem(), ["Error", f"Could not refresh state: {e}"])
                         error_item_tree.setForeground(0, QtGui.QBrush(QtGui.QColor("red")))
                         error_item_tree.setForeground(1, QtGui.QBrush(QtGui.QColor("red")))

            else:
                # Agent might have been deleted, mark for removal
                logger.warning(f"Agent {agent_id} not found during status refresh. Marking for removal.")
                items_to_remove.append(i)

        # Remove items marked for deletion (iterate backwards to avoid index issues)
        if items_to_remove:
            for i in sorted(items_to_remove, reverse=True):
                removed_item = self.agent_list_widget.takeItem(i)
                if removed_item:
                     removed_agent_id = removed_item.data(QtCore.Qt.UserRole)
                     # If the removed item was selected, clear details
                     if self.agent_detail_widget.current_agent_id == removed_agent_id:
                          self.agent_detail_widget.clear_details()
            # Optional: Schedule a full refresh just in case something was missed
            # QtCore.QTimer.singleShot(100, self.refresh_agent_list)

        # If no item is selected after refresh, clear details
        if not self.agent_list_widget.currentItem():
             self.agent_detail_widget.clear_details()


    def on_agent_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """Handles selection changes in the agent list."""
        if current_item:
            agent_id = current_item.data(QtCore.Qt.UserRole)
            if agent_id:
                agent = self.agent_manager.get_agent(agent_id)
                if agent:
                    logger.debug(f"Agent selected: {agent.name} ({agent_id})")
                    self.agent_detail_widget.update_details(agent)
                else:
                    logger.warning(f"Selected agent ID {agent_id} not found in manager.")
                    self.agent_detail_widget.clear_details()
                    # Maybe refresh list if agent is missing
                    self.refresh_agent_list()
            else:
                 # Handle non-agent items (like error messages)
                 self.agent_detail_widget.clear_details()
        else:
            # No item selected
            self.agent_detail_widget.clear_details()

    def open_add_agent_dialog(self):
        """Opens the dialog to add a new agent."""
        dialog = AddAgentDialog(self.agent_manager, self)
        if dialog.exec() == QDialog.Accepted:
            agent_data = dialog.get_agent_data()
            if agent_data:
                logger.info(f"Requesting creation of agent: {agent_data}")
                try:
                    # Use **agent_data to pass parameters correctly
                    new_agent = self.agent_manager.create_agent(**agent_data)
                    if new_agent:
                        logger.info(f"Agent '{new_agent.name}' created successfully.")
                        self.refresh_agent_list()
                        # Optionally select the newly created agent
                        for i in range(self.agent_list_widget.count()):
                             item = self.agent_list_widget.item(i)
                             if item.data(QtCore.Qt.UserRole) == new_agent.id:
                                  self.agent_list_widget.setCurrentItem(item)
                                  break
                    else:
                        # Agent creation might fail if type is unknown or other issues
                        QMessageBox.critical(self, "Agent Creation Failed", "Could not create the agent. Check logs for details.")
                except TypeError as te:
                     logger.error(f"TypeError during agent creation: {te}. Data: {agent_data}", exc_info=True)
                     QMessageBox.critical(self, "Agent Creation Error", f"Failed to create agent due to parameter mismatch:\n{te}\n\nCheck agent type requirements.")
                except Exception as e:
                    logger.error(f"Failed to create agent from dialog: {e}", exc_info=True)
                    QMessageBox.critical(self, "Agent Creation Error", f"Could not create agent:\n{e}")

# Note: Removed the agent type imports from the bottom as they are now
# handled within the AddAgentDialog's __init__ method's try-except block.
# This avoids potential module-level circular import issues.
