import logging
from PyQt5.QtCore import QObject, pyqtSignal

class LogViewerHandler(logging.Handler, QObject):
    """
    A custom logging handler that emits a PyQt signal for each log record.
    Connect this signal to a slot in the UI (e.g., a QTextEdit) to display logs.
    """
    log_signal = pyqtSignal(str)

    def __init__(self, log_signal: pyqtSignal, parent: QObject = None):
        """
        Initializes the handler.

        Args:
            log_signal: The PyQt signal to emit log messages on.
            parent: Optional parent QObject.
        """
        logging.Handler.__init__(self)
        QObject.__init__(self, parent)
        # Connect the internal signal to the one provided externally
        # This allows the handler to own the signal definition but emit on the one
        # passed from the LogViewer widget, ensuring it reaches the correct instance.
        # Note: Direct connection might be simpler if handler is always created with widget's signal.
        # self.log_signal.connect(log_signal) # Alternative approach
        self.external_log_signal = log_signal

    def emit(self, record: logging.LogRecord):
        """
        Formats the log record and emits it via the PyQt signal.
        """
        try:
            msg = self.format(record)
            # Emit the signal with the formatted message
            self.external_log_signal.emit(msg + '\n') # Add newline for display
        except Exception:
            self.handleError(record)

    # Optionally override handleError for more specific error handling
    # def handleError(self, record):
    #     """Handle errors which occur during an emit() call."""
    #     # Default implementation prints to stderr
    #     super().handleError(record)


