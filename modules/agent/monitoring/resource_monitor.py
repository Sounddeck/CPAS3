# filepath: modules/agent/monitoring/resource_monitor.py
import threading
import time
import logging

logger = logging.getLogger(__name__)

class ResourceMonitor:
    def __init__(self, interval=5):
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = None
        logger.info("ResourceMonitor initialized.")

    def start(self):
        if self._thread and self._thread.is_alive():
            logger.warning("ResourceMonitor already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor, daemon=True, name="ResourceMonitor")
        self._thread.start()
        logger.info("ResourceMonitor started.")

    def stop(self):
        if self._thread and self._thread.is_alive():
            logger.info("Stopping ResourceMonitor...")
            self._stop_event.set()
            self._thread.join(timeout=self.interval + 1)
            if self._thread.is_alive():
                 logger.warning("ResourceMonitor thread did not stop cleanly.")
            self._thread = None
            logger.info("ResourceMonitor stopped.")
        else:
             logger.info("ResourceMonitor not running.")


    def _monitor(self):
        logger.info("Resource monitoring loop started.")
        while not self._stop_event.wait(self.interval):
            try:
                # Placeholder: In real implementation, collect CPU/Memory usage
                # using libraries like psutil
                cpu_usage = 0.0 # psutil.cpu_percent()
                mem_usage = 0.0 # psutil.virtual_memory().percent
                logger.debug(f"Resource Usage - CPU: {cpu_usage}%, Memory: {mem_usage}% (Placeholder)")
            except Exception as e:
                logger.error(f"Error during resource monitoring: {e}", exc_info=True)
        logger.info("Resource monitoring loop finished.")
