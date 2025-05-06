# modules/ExampleModule/main.py

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class ModuleMain(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        label = QLabel("Hello from ExampleModule!")
        layout.addWidget(label)

        self.setLayout(layout)

    def get_name(self) -> str:
        return "Example Module"

    def get_description(self) -> str:
        return "This is a basic example module that displays a label."

    def shutdown(self):
        # Perform cleanup if needed
        pass
