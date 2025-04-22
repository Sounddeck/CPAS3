class AgentBackend:
    """Simulates backend operations for managing agents and tasks."""

    def __init__(self):
        # Initial list of agents
        self.agents = [
            {"id": 1, "name": "Agent 1", "status": "Running", "task": "Researching"},
            {"id": 2, "name": "Agent 2", "status": "Stopped", "task": "Idle"},
            {"id": 3, "name": "Agent 3", "status": "Running", "task": "Analyzing Data"}
        ]
        self.next_id = 4  # ID counter for new agents

        # Initial list of tasks
        self.tasks = [
            {"id": 1, "name": "Data Analysis", "agent_id": 3, "progress": 50, "priority": "High"},
            {"id": 2, "name": "Market Research", "agent_id": 1, "progress": 100, "priority": "Medium"},
            {"id": 3, "name": "Report Writing", "agent_id": None, "progress": 0, "priority": "Low"}
        ]
        self.next_task_id = 4  # ID counter for new tasks

    def get_agents(self):
        """Returns the list of agents."""
        return self.agents

    def get_tasks(self, sort_by="id"):
        """Returns the list of tasks, optionally sorted by a field."""
        if sort_by == "priority":
            # Sort tasks by priority (High -> Medium -> Low)
            priority_order = {"High": 1, "Medium": 2, "Low": 3}
            return sorted(self.tasks, key=lambda t: priority_order[t["priority"]])
        elif sort_by == "progress":
            # Sort tasks by progress (descending)
            return sorted(self.tasks, key=lambda t: t["progress"], reverse=True)
        elif sort_by == "name":
            # Sort tasks alphabetically by name
            return sorted(self.tasks, key=lambda t: t["name"].lower())
        return self.tasks

    def update_task_priority(self, task_id, priority):
        """Updates the priority of a task."""
        for task in self.tasks:
            if task["id"] == task_id:
                task["priority"] = priority
                return f"Priority of task '{task['name']}' updated to {priority}."
        return "Task not found."

    def update_task_progress(self, task_id, progress):
        """Updates the progress of a task."""
        for task in self.tasks:
            if task["id"] == task_id:
                task["progress"] = progress
                return f"Progress of task '{task['name']}' updated to {progress}%."
        return "Task not found."
