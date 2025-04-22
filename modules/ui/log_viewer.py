import logging

# Attempt Qt import
try:
    from PyQt6 import QtWidgets, QtCore, QtGui
    from PyQt6.QtCore import pyqtSlot, Qt
    from PyQt6.QtWidgets import QPlainTextEdit
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    # Define placeholders if Qt not available
    class QPlainTextEdit: pass
    def pyqtSlot(*args, **kwargs): return lambda func: func # Dummy decorator

# Get a logger for this module
logger = logging.getLogger(__name__)

# Define the LogViewer class
class LogViewer(QPlainTextEdit if QT_AVAILABLE else object):
    """
    A QPlainTextEdit widget specialized for displaying logs.
    Includes a slot to append messages.
    """
    def __init__(self, parent=None):
        if not QT_AVAILABLE:
            logger.error("LogViewer cannot be initialized, PyQt6 not available.")
            # Allow object creation but it won't be a widget
            super().__init__()
            return

        super().__init__(parent)
        self.setReadOnly(True)
        # Optional: Set a maximum block count to prevent memory issues
        self.setMaximumBlockCount(10000)
        logger.debug("LogViewer initialized.")

    @pyqtSlot(str)
    def append_log(self, message: str):
        """Slot to append a log message to the text edit."""
        # --- ADD LOGGING AT VERY START ---
        # Use logger directly, level 5 for ultra-verbose
        logger.log(5, f"LogViewer.append_log SLOT ENTERED. Message: {message[:100]}...")
        # --- END ADD LOGGING ---

        # Existing logging call (can keep or remove, the one above is more important now)
        # logging.log(5, f"UI SLOT: LogViewer.append_log received: {message[:100]}...")

        # Append the message using the base class method
        self.appendPlainText(message) # Use appendPlainText for QPlainTextEdit

        # Optional: Auto-scroll to the bottom
        self.ensureCursorVisible()

        # Optional: Limit block count again after append if needed, though setMaximumBlockCount is usually sufficient
        # current_block_count = self.blockCount()
        # max_blocks = 1000 # Example limit
        # if current_block_count > max_blocks:
        #     # Remove blocks from the beginning
        #     cursor = self.textCursor()
        #     cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
        #     cursor.movePosition(QtGui.QTextCursor.MoveOperation.Down, QtGui.QTextCursor.MoveMode.KeepAnchor, current_block_count - max_blocks)
        #     cursor.removeSelectedText()
        #     cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        #     self.setTextCursor(cursor)


# Example usage (if run directly)
if __name__ == '__main__':
    if QT_AVAILABLE:
        import sys
        app = QtWidgets.QApplication(sys.argv)
        viewer = LogViewer()
        viewer.setWindowTitle("Standalone LogViewer Test")
        viewer.show()
        # Example of manually calling the slot
        viewer.append_log("Test message 1.")
        viewer.append_log("Test message 2.\nWith newline.")
        sys.exit(app.exec())
    else:
        print("PyQt6 not available, cannot run LogViewer example.")
