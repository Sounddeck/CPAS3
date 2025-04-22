from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QPushButton, QInputDialog, QMessageBox, QTabWidget, QDialog, QLineEdit, QFormLayout
)
import sys
import qdarkstyle
from agent_backend import AgentBackend


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CPAS3 Application")
        self.agent_backend = AgentBackend()
        self.tab_widget = QTabWidget()  # Create a QTabWidget

        # Add tabs
        self.add_task_manager_tab()
        self.add_agent_manager_tab()

        # Set the QTabWidget as the central widget
        self.setCentralWidget(self.tab_widget)

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
