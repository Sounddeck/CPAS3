from react_agent import ReActAgent
from database import DatabaseManager

class ConversationalTutoring:
    def __init__(self):
        """
        Initialize the conversational tutoring module with the ReAct agent and database.
        """
        self.agent = ReActAgent()
        self.db = DatabaseManager()

    def handle_query(self, query):
        """
        Process the user's query and return a response from the ReAct agent.
        """
        # Query the ReAct agent
        response = self.agent.reason(query)

        # Log the interaction in the database
        self.db.log_interaction(input_text=query, response=response)

        return response

# Example usage
if __name__ == "__main__":
    tutor = ConversationalTutoring()
    user_query = input("Ask a question: ")
    print("Response:", tutor.handle_query(user_query))
