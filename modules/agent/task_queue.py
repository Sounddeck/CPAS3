import logging
import queue # Use the standard thread-safe queue
from typing import Optional

# Assuming AgentTask structure/import exists
try:
    from .models import AgentTask
except ImportError:
    logging.warning("Could not import AgentTask model for TaskQueue type hinting.")
    AgentTask = object # Placeholder

logger = logging.getLogger(__name__)

class TaskQueue:
    """
    A thread-safe queue for managing agent tasks using Python's standard queue.
    """
    def __init__(self):
        self._queue = queue.Queue() # Use standard queue.Queue
        logger.info("TaskQueue initialized using standard queue.Queue.")

    def put(self, task: AgentTask):
        """
        Adds a task to the queue. This is a blocking operation if the queue has size limits (not set here).
        """
        if task:
            self._queue.put(task)
            logger.debug(f"Task {task.task_id[:8]} added to the queue.")
        else:
            logger.warning("Attempted to add a None task to the queue.")

    def get(self) -> Optional[AgentTask]:
        """
        Retrieves a task from the queue. Blocks if the queue is empty.
        Returns None if a sentinel value indicating shutdown is received (optional).
        """
        try:
            # This will block the calling thread (the agent's thread) until an item is available
            task = self._queue.get()
            if task is None: # Handling a potential sentinel value for shutdown
                 logger.info("Received shutdown sentinel (None) from queue.")
                 return None
            logger.debug(f"Task {task.task_id[:8]} retrieved from the queue.")
            return task
        except Exception as e:
            # Should generally not happen with queue.Queue unless there's a logic error
            logger.error(f"Unexpected error getting task from queue: {e}", exc_info=True)
            return None

    def qsize(self) -> int:
        """Returns the approximate size of the queue."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Returns True if the queue is empty, False otherwise."""
        return self._queue.empty()

    def task_done(self):
        """Indicate that a formerly enqueued task is complete."""
        self._queue.task_done()

    def join(self):
        """Blocks until all items in the queue have been gotten and processed."""
        self._queue.join()

    def clear(self):
        """Removes all items from the queue."""
        with self._queue.mutex:
            self._queue.queue.clear()
        logger.info("Task queue cleared.")

