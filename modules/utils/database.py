import sqlite3

class DatabaseManager:
    def __init__(self, db_name="cpas.db"):
        """
        Initialize the database manager and create necessary tables.
        """
        self.connection = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        """
        Create tables for agents, tasks, and interactions.
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                task TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                priority TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                agent_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

    def add_agent(self, name, status="Stopped", task=None):
        """
        Add a new agent to the database.
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO agents (name, status, task) VALUES (?, ?, ?)
        """, (name, status, task))
        self.connection.commit()

    def add_task(self, name, priority, agent_id=None):
        """
        Add a new task to the database.
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO tasks (name, priority, agent_id) VALUES (?, ?, ?)
        """, (name, priority, agent_id))
        self.connection.commit()

    def log_interaction(self, input_text, response):
        """
        Log an interaction between the user and the system.
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO interactions (input, response) VALUES (?, ?)
        """, (input_text, response))
        self.connection.commit()

    def get_agents(self):
        """
        Fetch all agents from the database.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM agents")
        return cursor.fetchall()

    def get_tasks(self):
        """
        Fetch all tasks from the database.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM tasks")
        return cursor.fetchall()

    def close(self):
        """
        Close the database connection.
        """
        self.connection.close()
