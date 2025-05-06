# agent_instance.py

from langchain.agents import initialize_agent, Tool
from langchain.chat_models import ChatOpenAI
from langchain.tools import DuckDuckGoSearchRun
from langchain.memory import MongoDBChatMessageHistory, ConversationBufferMemory
import os

# Set your OpenAI key
os.environ["OPENAI_API_KEY"] = "your-openai-key"

# MongoDB setup
MONGO_URI = "mongodb://localhost:27017"
SESSION_ID = "cpas-session"

# MongoDB-based memory
chat_history = MongoDBChatMessageHistory(
    connection_string=MONGO_URI,
    session_id=SESSION_ID,
    database_name="cpas_memory",
    collection_name="messages"
)
memory = ConversationBufferMemory(
    memory_key="chat_history",
    chat_memory=chat_history,
    return_messages=True
)

# Tool example
search = DuckDuckGoSearchRun()

tools = [
    Tool(
        name="Search",
        func=search.run,
        description="Searches the web for current information"
    )
]

# Initialize LangChain agent
llm = ChatOpenAI(temperature=0)

agent = initialize_agent(
    tools,
    llm,
    agent="chat-conversational-react-description",
    memory=memory,
    verbose=True
)

def run_agent(prompt: str) -> str:
    """Run the agent with a user prompt"""
    return agent.run(prompt)
