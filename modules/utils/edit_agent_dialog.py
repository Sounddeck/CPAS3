from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt


class EditAgentDialog(QDialog):
    def __init__(self, agent_data=None, parent=None):
        """
        Initializes the EditAgentDialog.
        :param agent_data: Dictionary containing agent details (id, name, status, task).
        :param parent: Parent widget (optional).
        """
        super().__init__(parent)
        self.setWindowTitle("Edit Agent")
        self.setFixedSize(400, 300)

        # Agent data
        self.agent_data = agent_data or {"id": None, "name": "", "status": "Stopped", "task": ""}

        # Main layout
        layout = QVBoxLayout(self)
        
        # Name field
        layout.addWidget(QLabel("Agent Name:"))
        self.name_input = QLineEdit(self.agent_data["name"])
        layout.addWidget(self.name_input)
        
        # Status dropdown
        layout.addWidget(QLabel("Agent Status:"))
        self.status_dropdown = QComboBox()
        self.status_dropdown.addItems(["Running", "Stopped"])
        self.status_dropdown.setCurrentText(self.agent_data["status"])
        layout.addWidget(self.status_dropdown)
        
        # Task field
        layout.addWidget(QLabel("Agent Task:"))
        self.task_input = QLineEdit(self.agent_data["task"])
        layout.addWidget(self.task_input)
        
        # Save and Cancel buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # Button actions
        self.save_button.clicked.connect(self.save)
        self.cancel_button.clicked.connect(self.reject)

    def save(self):
        """Save the agent data and close the dialog."""
        name = self.name_input.text().strip()
        status = self.status_dropdown.currentText()
        task = self.task_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Agent name cannot be empty.")
            return

        self.agent_data.update({"name": name, "status": status, "task": task})
        self.accept()  # Close the dialog and indicate success

    def get_agent_data(self):
        """Returns the updated agent data."""
        return self.agent_data
