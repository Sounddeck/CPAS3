import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class StructuredMemory:
    """
    Handles persistent storage and retrieval of structured data, primarily events,
    using an SQLite database.
    """

    def __init__(self, db_path: str = "cpas_memory.db"):
        """
        Initializes the StructuredMemory instance and connects to the database.

        Args:
            db_path (str): The path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        try:
            # Connect to the DB. Creates the file if it doesn't exist.
            # isolation_level=None enables autocommit mode for simplicity here,
            # but consider transaction management for more complex operations.
            self.conn = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
            self.cursor = self.conn.cursor()
            self._initialize_db()
            logger.info(f"Successfully connected to structured memory database: {db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection error to {db_path}: {e}", exc_info=True)
            # Depending on requirements, you might want to raise the exception
            # or handle it in a way that allows the application to continue degraded.
            self.conn = None
            self.cursor = None
        except Exception as e:
             logger.error(f"An unexpected error occurred during database initialization: {e}", exc_info=True)
             # Handle unexpected errors during setup
             self.conn = None
             self.cursor = None


    def _initialize_db(self):
        """Creates the necessary tables if they don't exist."""
        if not self.cursor:
             logger.error("Cannot initialize DB: Cursor is not available.")
             return
        try:
            # --- Events Table ---
            # Stores timestamped events with type, source, details (JSON), and correlation ID.
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_iso TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    details_json TEXT,
                    correlation_id TEXT
                );
                """
            )
            # Add indexes for faster querying
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp_iso);")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events (event_type);")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events (source);")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_correlation_id ON events (correlation_id);")

            # --- State Table (Example - adapt as needed) ---
            # Stores key-value pairs for general state persistence.
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    last_updated_iso TEXT NOT NULL
                );
                """
            )

            # --- Agent Knowledge Table (Example - adapt as needed) ---
            # Could store facts or learned information associated with agents.
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    fact_type TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    added_iso TEXT NOT NULL,
                    source_event_id INTEGER,
                    FOREIGN KEY (source_event_id) REFERENCES events(id)
                );
                """
            )
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_agent_id ON agent_knowledge (agent_id);")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_fact_type ON agent_knowledge (fact_type);")

            logger.debug("Database tables ensured to exist.")

        except sqlite3.Error as e:
            logger.error(f"Error initializing database tables: {e}", exc_info=True)
            # Handle or raise the error appropriately

    def log_event(
        self,
        event_type: str,
        source: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Logs an event to the 'events' table.

        Args:
            event_type (str): The type of event (e.g., 'USER_INPUT', 'AGENT_ACTION').
            source (str): The origin of the event (e.g., 'AgentManager', 'Agent-XYZ').
            details (Optional[Dict[str, Any]]): A dictionary containing event-specific data.
                                                Must be JSON serializable. Defaults to None.
            correlation_id (Optional[str]): An ID to link related events. Defaults to None.
            timestamp (Optional[datetime]): The timestamp of the event. Defaults to now (UTC).
                                            If provided, ensure it's timezone-aware (UTC recommended).
        """
        if not self.cursor or not self.conn:
            logger.error("Cannot log event: Database connection not available.")
            return

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif timestamp.tzinfo is None:
             logger.warning("Provided timestamp is naive. Assuming UTC.")
             timestamp = timestamp.replace(tzinfo=timezone.utc)

        timestamp_iso = timestamp.isoformat()
        details_json = json.dumps(details) if details else None

        try:
            self.cursor.execute(
                """
                INSERT INTO events (timestamp_iso, event_type, source, details_json, correlation_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp_iso, event_type, source, details_json, correlation_id),
            )
            # self.conn.commit() # Not needed if isolation_level=None (autocommit)
            logger.debug(f"Logged event: Type={event_type}, Source={source}, CorrID={correlation_id}")
        except sqlite3.Error as e:
            logger.error(f"Database error logging event: {e}", exc_info=True)
        except TypeError as e:
             logger.error(f"Error serializing event details to JSON: {e}. Details: {details}", exc_info=True)


    def query_events(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
        start_time_iso: Optional[str] = None,
        end_time_iso: Optional[str] = None,
        limit: Optional[int] = None,
        order_by_timestamp_desc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Queries the 'events' table based on specified criteria.

        Args:
            event_type (Optional[str]): Filter by event type.
            source (Optional[str]): Filter by event source.
            correlation_id (Optional[str]): Filter by correlation ID.
            start_time_iso (Optional[str]): Filter events occurring at or after this ISO timestamp.
            end_time_iso (Optional[str]): Filter events occurring at or before this ISO timestamp.
            limit (Optional[int]): Maximum number of events to return.
            order_by_timestamp_desc (bool): If True, order by timestamp descending (newest first).
                                           If False, order ascending (oldest first).

        Returns:
            List[Dict[str, Any]]: A list of events matching the criteria, where each event
                                  is a dictionary. Returns empty list on error or no results.
        """
        if not self.cursor:
            logger.error("Cannot query events: Database connection not available.")
            return []

        query = "SELECT id, timestamp_iso, event_type, source, details_json, correlation_id FROM events WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if source:
            query += " AND source = ?"
            params.append(source)
        if correlation_id:
            query += " AND correlation_id = ?"
            params.append(correlation_id)
        if start_time_iso:
            query += " AND timestamp_iso >= ?"
            params.append(start_time_iso)
        if end_time_iso:
            query += " AND timestamp_iso <= ?"
            params.append(end_time_iso)

        query += f" ORDER BY timestamp_iso {'DESC' if order_by_timestamp_desc else 'ASC'}"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        try:
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            # Convert rows to dictionaries and parse JSON details
            results = []
            for row in rows:
                event_dict = dict(row)
                if event_dict.get('details_json'):
                    try:
                        event_dict['details'] = json.loads(event_dict['details_json'])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode details_json for event ID {event_dict.get('id')}")
                        event_dict['details'] = None # Or keep raw JSON / add error marker
                else:
                    event_dict['details'] = None
                # del event_dict['details_json'] # Optionally remove the raw JSON string
                results.append(event_dict)
            return results
        except sqlite3.Error as e:
            logger.error(f"Database error querying events: {e}", exc_info=True)
            return []

    # --- Example State Management ---

    def set_state(self, key: str, value: Dict[str, Any]):
        """Stores or updates a key-value pair in the state table."""
        if not self.cursor or not self.conn:
            logger.error("Cannot set state: Database connection not available.")
            return
        try:
            value_json = json.dumps(value)
            timestamp_iso = datetime.now(timezone.utc).isoformat()
            self.cursor.execute(
                """
                INSERT INTO state (key, value_json, last_updated_iso)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    last_updated_iso = excluded.last_updated_iso;
                """,
                (key, value_json, timestamp_iso)
            )
            # self.conn.commit() # Autocommit
            logger.debug(f"Set state for key: {key}")
        except sqlite3.Error as e:
            logger.error(f"Database error setting state for key '{key}': {e}", exc_info=True)
        except TypeError as e:
             logger.error(f"Error serializing state value to JSON for key '{key}': {e}. Value: {value}", exc_info=True)


    def get_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a value from the state table by key."""
        if not self.cursor:
            logger.error("Cannot get state: Database connection not available.")
            return None
        try:
            self.cursor.execute("SELECT value_json FROM state WHERE key = ?", (key,))
            row = self.cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value_json'])
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON for state key '{key}'")
                    return None
            else:
                return None
        except sqlite3.Error as e:
            logger.error(f"Database error getting state for key '{key}': {e}", exc_info=True)
            return None

    def delete_state(self, key: str) -> bool:
        """Deletes a key-value pair from the state table."""
        if not self.cursor or not self.conn:
            logger.error("Cannot delete state: Database connection not available.")
            return False
        try:
            self.cursor.execute("DELETE FROM state WHERE key = ?", (key,))
            # self.conn.commit() # Autocommit
            deleted = self.cursor.rowcount > 0
            if deleted:
                logger.debug(f"Deleted state for key: {key}")
            return deleted
        except sqlite3.Error as e:
            logger.error(f"Database error deleting state for key '{key}': {e}", exc_info=True)
            return False


    def close(self):
        """Closes the database connection."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Structured memory database connection closed.")
                self.conn = None
                self.cursor = None
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)

    def __del__(self):
        """Ensures the connection is closed when the object is garbage collected."""
        self.close()

# Example usage (for testing purposes)
if __name__ == "__main__":
    print("Running StructuredMemory example...")
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Use an in-memory database for this example for easy cleanup
    # Replace with a file path for persistence: e.g., "test_memory.db"
    memory = StructuredMemory(db_path=":memory:")
    # memory = StructuredMemory(db_path="test_memory.db") # Use file

    if memory.conn: # Proceed only if connection was successful
        print("\n--- Logging Events ---")
        memory.log_event("USER_INPUT", "Console", {"text": "Hello CPAS!"}, "conv1")
        memory.log_event("AGENT_ACTION", "PlannerAgent", {"action": "create_plan", "goal": "Test"}, "conv1")
        memory.log_event("SYSTEM_STATUS", "AgentManager", {"status": "running"})
        memory.log_event("AGENT_ACTION", "ExecutorAgent", {"action": "execute_step", "step": 1}, "conv1")
        memory.log_event("USER_INPUT", "Console", {"text": "Show me results"}, "conv2") # Different conversation

        print("\n--- Querying Events ---")
        print("Last 3 events:")
        last_3 = memory.query_events(limit=3)
        for event in reversed(last_3): # Print oldest first
             print(f"- {event['timestamp_iso']} [{event['event_type']}] ({event['source']}) CorrID: {event['correlation_id']} Details: {event['details']}")

        print("\nEvents for conversation 'conv1':")
        conv1_events = memory.query_events(correlation_id="conv1", order_by_timestamp_desc=False)
        for event in conv1_events:
             print(f"- {event['timestamp_iso']} [{event['event_type']}] ({event['source']}) Details: {event['details']}")

        print("\n'AGENT_ACTION' events:")
        agent_actions = memory.query_events(event_type="AGENT_ACTION")
        for event in agent_actions:
            print(f"- {event['timestamp_iso']} ({event['source']}) Details: {event['details']}")


        print("\n--- Managing State ---")
        memory.set_state("user_prefs", {"theme": "dark", "language": "en"})
        memory.set_state("active_conversation", {"id": "conv1", "last_message_id": 123})

        prefs = memory.get_state("user_prefs")
        print(f"Retrieved user_prefs: {prefs}")

        active_conv = memory.get_state("active_conversation")
        print(f"Retrieved active_conversation: {active_conv}")

        print("Updating active_conversation...")
        memory.set_state("active_conversation", {"id": "conv1", "last_message_id": 456})
        active_conv_updated = memory.get_state("active_conversation")
        print(f"Retrieved updated active_conversation: {active_conv_updated}")

        print("Deleting user_prefs...")
        deleted = memory.delete_state("user_prefs")
        print(f"Deleted successfully? {deleted}")
        prefs_after_delete = memory.get_state("user_prefs")
        print(f"Retrieved user_prefs after delete: {prefs_after_delete}")


        print("\n--- Closing Connection ---")
        memory.close()
    else:
        print("\nFailed to initialize StructuredMemory. Cannot run examples.")

    print("\nStructuredMemory example finished.")

    # If using a file DB, you might want to delete it after the test
    # import os
    # if os.path.exists("test_memory.db"):
    #     os.remove("test_memory.db")
    #     print("Removed test_memory.db")
