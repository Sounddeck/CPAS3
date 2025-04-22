import logging

# Attempt to import Qt, handle gracefully if unavailable
try:
    from PyQt6.QtCore import QObject, pyqtSignal
    QT_AVAILABLE = True

    # Define the handler only if Qt is available
    class QtLogHandler(logging.Handler, QObject):
        """
        A logging handler that emits a Qt signal for each log record.

        Connect the 'log_signal' to a slot (e.g., a method on a QPlainTextEdit)
        that expects a string argument.
        """
        # Define the signal within the class body
        log_signal = pyqtSignal(str)

        def __init__(self, slot_receiver_func, level=logging.NOTSET):
            """
            Initializes the handler.

            Args:
                slot_receiver_func: The Qt slot (or any callable) to connect the signal to.
                                    This is kept for potential direct connection if needed,
                                    but the primary mechanism is emitting the signal.
                level: The minimum logging level for this handler.
            """
            # Initialize base classes
            logging.Handler.__init__(self, level=level)
            QObject.__init__(self) # Initialize QObject part

            # Store the logger for internal messages
            self.internal_logger = logging.getLogger(__name__)
            self.internal_logger.debug("QtLogHandler initialized.")

            # Connect the signal to the provided slot function
            # Note: The connection is now primarily done in MainWindow _setup_ui
            # self.log_signal.connect(slot_receiver_func)
            # self.internal_logger.debug(f"Connected log_signal to {slot_receiver_func}")


        def emit(self, record):
            """
            Formats the log record and emits the log_signal.

            Args:
                record: The LogRecord object.
            """
            try:
                # Format the message using the handler's formatter
                msg = self.format(record)
                # --- ADD LOGGING BEFORE EMIT ---
                # Use a low level to avoid potential loops if this logger also uses the handler
                self.internal_logger.log(5, f"QtLogHandler emitting signal with message: {msg[:100]}...")
                # --- END ADD LOGGING ---
                # Emit the signal with the formatted message
                self.log_signal.emit(msg)
            except Exception:
                # Handle exceptions during formatting or emitting
                self.handleError(record)

        # Override handle to ensure emit is called (though Handler.handle usually calls emit)
        def handle(self, record):
            """
            Conditionally emits a message for specified record.
            """
            # --- ADD LOGGING AT START OF HANDLE ---
            self.internal_logger.log(5, f"QtLogHandler handle called for record from: {record.name}, level: {record.levelname}")
            # --- END ADD LOGGING ---
            if self.filter(record):
                self.emit(record)


except ImportError:
    QT_AVAILABLE = False
    # Define a dummy handler if Qt is not available, so imports don't break
    class QtLogHandler(logging.Handler):
        log_signal = None # No signal
        def __init__(self, slot_receiver_func, level=logging.NOTSET):
            super().__init__(level=level)
            logging.getLogger(__name__).warning("PyQt6 not found. QtLogHandler is disabled.")
        def emit(self, record):
            pass # Do nothing

# Example usage (if run directly, though not typical for a handler module)
if __name__ == '__main__':
    # This is just for basic testing of the handler itself
    if QT_AVAILABLE:
        from PyQt6.QtWidgets import QApplication, QPlainTextEdit
        import sys

        # Basic Qt application setup
        app = QApplication(sys.argv)
        log_viewer = QPlainTextEdit()
        log_viewer.setWindowTitle("Test Log Viewer")
        log_viewer.setReadOnly(True)

        # Setup logging
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Create and add the Qt handler
        # Connect directly for this simple test
        qt_handler = QtLogHandler(log_viewer.appendPlainText)
        qt_handler.setLevel(logging.DEBUG) # Set handler level
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        qt_handler.setFormatter(formatter)
        root_logger.addHandler(qt_handler)

        # Add a console handler too
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Show the viewer
        log_viewer.show()

        # Log some messages
        logging.debug("This is a debug message.")
        logging.info("This is an info message.")
        logging.warning("This is a warning message.")
        logging.error("This is an error message.")

        # Start the Qt event loop
        sys.exit(app.exec())
    else:
        print("PyQt6 is not available, cannot run QtLogHandler example.")
