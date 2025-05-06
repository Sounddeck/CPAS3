"""
Update main_desktop.py to use SimpleAgent
"""

import os
import sys

def update_main_desktop():
    """
    Update main_desktop.py to use SimpleAgent
    """
    # Read the original main_desktop.py
    with open("main_desktop.py", "r") as f:
        content = f.read()
    
    # First, back up the original file
    with open("main_desktop.py.bak2", "w") as f:
        f.write(content)
    
    # Replace SimpleReActAgent import with SimpleAgent
    content = content.replace(
        "from src.agents.simple_react_agent import SimpleReActAgent",
        "from src.agents.simple_agent import SimpleAgent"
    )
    
    # Replace SimpleReActAgent usage with SimpleAgent
    content = content.replace("SimpleReActAgent(", "SimpleAgent(")
    
    # Write the updated content
    with open("main_desktop.py", "w") as f:
        f.write(content)
    
    print("Successfully updated main_desktop.py to use SimpleAgent")

if __name__ == "__main__":
    update_main_desktop()
