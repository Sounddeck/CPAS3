import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Tracks performance metrics for agents and tasks."""

    def __init__(self):
        # Store logs per agent, keyed by agent_id
        # Each log entry will be a dictionary
        self.task_logs = defaultdict(list)
        logger.info("PerformanceTracker initialized.")

    def log_task_performance(
        self,
        agent_id: str,
        task_id: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        success: bool
    ):
        """Logs the completion details of a specific task."""
        timestamp = datetime.utcnow() # Log when the tracking record is created
        duration: Optional[float] = None

        # Calculate duration if start and end times are valid
        if isinstance(start_time, datetime) and isinstance(end_time, datetime):
             try:
                  duration = (end_time - start_time).total_seconds()
             except TypeError:
                  logger.warning(f"Could not calculate duration for task {task_id} (agent {agent_id}). Timestamps: start={start_time}, end={end_time}")
                  duration = None # Ensure duration is None if calculation fails
        elif start_time or end_time: # Log if only one is present
             logger.warning(f"Missing start or end time for task {task_id} (agent {agent_id}). Cannot calculate duration accurately. Start: {start_time}, End: {end_time}")


        log_entry = {
            "task_id": task_id,
            "log_timestamp": timestamp, # When this record was created
            "start_time": start_time, # Actual task start time
            "end_time": end_time,     # Actual task end time
            "duration_seconds": duration, # Calculated duration
            "success": success,
        }
        self.task_logs[agent_id].append(log_entry)
        duration_str = f"{duration:.2f}s" if duration is not None else "N/A"
        logger.debug(f"Logged performance for task {task_id} (agent {agent_id}): duration={duration_str}, success={success}")

    def get_agent_performance_logs(self, agent_id: str) -> list:
        """Retrieves all performance log entries for a specific agent."""
        return self.task_logs.get(agent_id, [])

    def get_summary(self, agent_id: str) -> dict:
        """Calculates summary statistics for an agent based on logged tasks."""
        logs = self.get_agent_performance_logs(agent_id)
        if not logs:
            return {"task_count": 0, "success_rate": 0, "avg_duration_seconds": 0}

        total_tasks = len(logs)
        successful_tasks = sum(1 for log in logs if log["success"])
        # Calculate duration only for tasks where it's available
        valid_durations = [log["duration_seconds"] for log in logs if log["duration_seconds"] is not None]
        total_duration = sum(valid_durations)
        num_tasks_with_duration = len(valid_durations)

        success_rate = (successful_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        avg_duration = total_duration / num_tasks_with_duration if num_tasks_with_duration > 0 else 0

        return {
            "task_count": total_tasks,
            "success_rate": f"{success_rate:.1f}%", # Format as percentage string
            "avg_duration_seconds": round(avg_duration, 2) if avg_duration is not None else None,
            "tasks_with_duration": num_tasks_with_duration
        }

    def clear_logs(self, agent_id: Optional[str] = None):
         """Clears performance logs for a specific agent or all agents."""
         if agent_id:
              if agent_id in self.task_logs:
                   del self.task_logs[agent_id]
                   logger.info(f"Cleared performance logs for agent {agent_id}.")
              else:
                   logger.warning(f"No performance logs found for agent {agent_id} to clear.")
         else:
              self.task_logs.clear()
              logger.info("Cleared performance logs for all agents.")

