import queue
import uuid
import logging
import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import threading

# Import signal emitter safely
try:
    from ..ui.signal_emitter import signal_emitter
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False
    # Define a dummy emitter if UI is not available
    class DummySignalEmitter:
        def __getattr__(self, name):
            # Return a dummy signal that does nothing when emitted
            class DummySignal:
                def emit(self, *args, **kwargs): pass
            return DummySignal()
    signal_emitter = DummySignalEmitter()
    # logging.info("TaskQueue running without UI signal emitter.") # Less verbose

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Represents the status of a task in the queue."""
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED" # Agent has picked it up
    IN_PROGRESS = "IN_PROGRESS" # Agent is actively working on it
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED" # Explicitly cancelled

class Task:
    """Represents a task to be executed by an agent."""
    def __init__(
        self,
        description: str,
        task_id: Optional[str] = None,
        target_agent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        priority: int = 0 # Lower number means higher priority
    ):
        self.task_id = task_id or uuid.uuid4().hex
        self.description = description
        self.target_agent_id = target_agent_id # Specific agent or None for any
        self.data = data or {}
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = self.created_at
        self.assigned_agent_id: Optional[str] = None
        self.result: Optional[Any] = None
        self.error_message: Optional[str] = None

        logger.debug(f"Task created - ID: {self.task_id[:8]}, Desc: '{self.description[:50]}...', Target: {self.target_agent_id or 'Any'}")

    def update_status(self, status: TaskStatus, agent_id: Optional[str] = None, result: Optional[Any] = None, error: Optional[str] = None):
        """Updates the task's status and associated info."""
        if self.status != status:
            old_status = self.status
            self.status = status
            self.updated_at = datetime.datetime.now(datetime.timezone.utc)
            if agent_id:
                self.assigned_agent_id = agent_id
            if result is not None:
                self.result = result
            if error is not None:
                self.error_message = error

            logger.info(f"Task {self.task_id[:8]} status changed from {old_status.name} to {status.name}. Agent: {agent_id or 'N/A'}")
            try:
                # Emit signal with updated task details
                signal_emitter.task_status_updated.emit(self.to_dict())
            except Exception as sig_e:
                logger.error(f"Error emitting task_status_updated signal for {self.task_id[:8]}: {sig_e}", exc_info=False)


    def to_dict(self) -> Dict[str, Any]:
         """Returns a dictionary representation of the task."""
         return {
              "task_id": self.task_id,
              "description": self.description,
              "target_agent_id": self.target_agent_id,
              "assigned_agent_id": self.assigned_agent_id,
              "data": self.data,
              "priority": self.priority,
              "status": self.status.name, # Store enum name
              "result": self.result,
              "error_message": self.error_message,
              "created_at": self.created_at.isoformat(),
              "updated_at": self.updated_at.isoformat(),
         }

    # Allow comparison for priority queue
    def __lt__(self, other):
        if not isinstance(other, Task):
            return NotImplemented
        return self.priority < other.priority

class TaskQueue:
    """
    Manages a queue of tasks for agents, supporting priority and status tracking.
    Uses a thread-safe PriorityQueue.
    """
    def __init__(self):
        self._queue = queue.PriorityQueue()
        self._all_tasks: Dict[str, Task] = {} # Store all tasks ever added for status tracking
        self._lock = threading.Lock() # Protect access to _all_tasks dict
        logger.info("TaskQueue initialized.")

    def add_task(self, task: Task):
        """Adds a task to the priority queue and tracking dictionary."""
        if not isinstance(task, Task):
            raise TypeError("Only Task objects can be added to the queue.")

        with self._lock:
            if task.task_id in self._all_tasks:
                logger.warning(f"Task with ID {task.task_id[:8]} already exists. Ignoring add request.")
                return
            self._all_tasks[task.task_id] = task # Track the task

        # PriorityQueue takes tuples: (priority, task_object)
        self._queue.put((task.priority, task))
        logger.info(f"Task {task.task_id[:8]} added to queue with priority {task.priority}. Queue size: {self.size()}")
        # Emit signal after adding
        try:
            signal_emitter.task_created.emit(task.to_dict()) # Emit full task data
        except Exception as sig_e:
            logger.error(f"Error emitting task_created signal for {task.task_id[:8]}: {sig_e}", exc_info=False)


    def get_task(self, agent_id: str, block: bool = True, timeout: Optional[float] = None) -> Optional[Task]:
        """
        Retrieves the highest priority task suitable for the given agent_id.
        If no specific task is available, it tries to get a general task (target_agent_id is None).
        Updates task status to ASSIGNED.

        Returns None if the queue is empty or timeout occurs.
        """
        # Note: PriorityQueue doesn't allow direct searching for specific target_agent_id.
        # We might need to get items and put them back if they aren't suitable.
        # This is inefficient. A better approach might involve multiple queues or a different data structure
        # if targeted tasks are very common and performance is critical.
        # For now, we'll try a simpler approach: get the highest priority task and check if it's targeted.
        # This assumes agents capable of handling general tasks will check the queue periodically.

        try:
            # Get the highest priority item (priority, task)
            priority, task = self._queue.get(block=block, timeout=timeout)

            with self._lock:
                # Double-check if task still exists in our tracking (could be cancelled)
                if task.task_id not in self._all_tasks or self._all_tasks[task.task_id].status == TaskStatus.CANCELLED:
                     logger.info(f"Task {task.task_id[:8]} retrieved from queue but was already cancelled or removed. Discarding.")
                     self._queue.task_done() # Mark as processed even if discarded
                     return None # Try getting another task in the next agent loop iteration

                # Check if the task is targeted and if it matches the requesting agent
                if task.target_agent_id and task.target_agent_id != agent_id:
                    # This task is for someone else. Put it back.
                    logger.debug(f"Task {task.task_id[:8]} is targeted for {task.target_agent_id}, not {agent_id}. Re-queueing.")
                    self._queue.put((priority, task)) # Put it back with original priority
                    # We can't easily get the *next* best task for *this* agent without potentially
                    # cycling through many items. Return None for now, agent should retry.
                    return None
                else:
                    # Task is either general or targeted to this agent. Assign it.
                    task.update_status(TaskStatus.ASSIGNED, agent_id=agent_id)
                    logger.info(f"Task {task.task_id[:8]} assigned to agent {agent_id}. Desc: '{task.description[:50]}...'")
                    # We don't call task_done yet - that happens when the agent *completes* it.
                    return task

        except queue.Empty:
            # logger.debug("Task queue is empty.") # Can be noisy
            return None
        except Exception as e:
             logger.error(f"Error getting task from queue: {e}", exc_info=True)
             return None

    def complete_task(self, task_id: str, result: Optional[Any] = None):
        """Marks a task as completed by the agent."""
        with self._lock:
            task = self._all_tasks.get(task_id)
            if task:
                if task.status not in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]:
                     logger.warning(f"Attempting to complete task {task_id[:8]} which is in status {task.status.name}, not ASSIGNED/IN_PROGRESS.")
                     # Allow completion anyway? Or raise error? For now, allow.
                task.update_status(TaskStatus.COMPLETED, result=result)
                logger.info(f"Task {task_id[:8]} marked as COMPLETED by agent {task.assigned_agent_id}.")
                # Find the corresponding item in the queue to mark done? Difficult with PriorityQueue.
                # Let's assume task_done() signifies processing attempt is finished, not necessarily success.
                # The agent calling get_task() implicitly calls task_done() when it's truly finished.
                # We need a way to signal queue processing is done. Let's rely on agent logic for now.
                # self._queue.task_done() # This should be called by the worker that got the task
            else:
                logger.warning(f"Task {task_id[:8]} not found to mark as complete.")

    def fail_task(self, task_id: str, error_message: str):
         """Marks a task as failed."""
         with self._lock:
             task = self._all_tasks.get(task_id)
             if task:
                 if task.status not in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]:
                      logger.warning(f"Attempting to fail task {task_id[:8]} which is in status {task.status.name}, not ASSIGNED/IN_PROGRESS.")
                 task.update_status(TaskStatus.FAILED, error=error_message)
                 logger.info(f"Task {task_id[:8]} marked as FAILED by agent {task.assigned_agent_id}. Error: {error_message}")
                 # self._queue.task_done() # See comment in complete_task
             else:
                 logger.warning(f"Task {task_id[:8]} not found to mark as failed.")

    def update_task_progress(self, task_id: str, agent_id: Optional[str] = None):
         """Marks a task as actively in progress."""
         with self._lock:
             task = self._all_tasks.get(task_id)
             if task:
                  if task.status == TaskStatus.ASSIGNED:
                       task.update_status(TaskStatus.IN_PROGRESS, agent_id=agent_id or task.assigned_agent_id)
                       logger.debug(f"Task {task_id[:8]} marked as IN_PROGRESS by agent {agent_id or task.assigned_agent_id}.")
                  elif task.status == TaskStatus.IN_PROGRESS:
                       pass # Already in progress
                  else:
                       logger.warning(f"Cannot mark task {task_id[:8]} as IN_PROGRESS, status is {task.status.name}.")
             else:
                  logger.warning(f"Task {task_id[:8]} not found to mark as IN_PROGRESS.")


    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Gets the status of a specific task."""
        with self._lock:
            task = self._all_tasks.get(task_id)
            return task.status if task else None

    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
         """Gets the full details of a specific task."""
         with self._lock:
             task = self._all_tasks.get(task_id)
             return task.to_dict() if task else None

    def get_all_tasks(self) -> List[Dict[str, Any]]:
         """Gets details for all tasks currently tracked."""
         with self._lock:
              return [task.to_dict() for task in self._all_tasks.values()]

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
         """Gets details for all tasks currently pending."""
         with self._lock:
              return [task.to_dict() for task in self._all_tasks.values() if task.status == TaskStatus.PENDING]


    def size(self) -> int:
        """Returns the approximate number of tasks currently in the queue."""
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """Checks if the queue is empty."""
        return self._queue.empty()

    # --- Methods related to queue joining (less common for persistent agents) ---
    def join(self):
        """Blocks until all items in the queue have been gotten and processed."""
        # Note: This relies on consumers calling task_done() appropriately.
        # Our agents might not call task_done() immediately after get_task().
        # Use with caution in a long-running agent scenario.
        logger.info("Waiting for all tasks in the queue to be processed...")
        self._queue.join()
        logger.info("All tasks in the queue have been processed.")

    def task_done(self, task_id: str):
         """
         Indicates that a formerly enqueued task is complete.
         Used by queue consumers. Decrements the count of unfinished tasks.
         If join() is currently blocking, it will resume when the count of unfinished
         tasks becomes zero.
         """
         # We need to find the task to ensure it exists, but the call is really for the queue itself.
         with self._lock:
              task = self._all_tasks.get(task_id)
              if not task:
                   logger.warning(f"task_done called for non-existent task ID {task_id[:8]}.")
                   # Cannot call self._queue.task_done() without a corresponding get()
                   return

         try:
              # This signals to the queue itself, not related to our Task object status
              self._queue.task_done()
              logger.debug(f"task_done() called for task {task_id[:8]}.")
         except ValueError:
              logger.error(f"task_done() called for task {task_id[:8]} more times than items placed in queue.", exc_info=True)
         except Exception as e:
              logger.error(f"Error calling task_done() for task {task_id[:8]}: {e}", exc_info=True)

