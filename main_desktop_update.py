"""
Update main_desktop.py to use SimpleReActAgent
"""

import os
import sys

def update_main_desktop():
    """
    Update main_desktop.py to use SimpleReActAgent
    """
    # Read the original main_desktop.py
    with open("main_desktop.py", "r") as f:
        content = f.read()
    
    # First, back up the original file
    with open("main_desktop.py.bak", "w") as f:
        f.write(content)
    
    # Replace ReActAgent import with SimpleReActAgent
    content = content.replace(
        "from src.agents.react_agent import ReActAgent",
        "from src.agents.simple_react_agent import SimpleReActAgent"
    )
    
    # Replace ReActAgent usage with SimpleReActAgent
    content = content.replace("ReActAgent(", "SimpleReActAgent(")
    
    # Remove the memory patch if it was added
    lines = content.split("\n")
    filtered_lines = []
    skip_section = False
    
    for line in lines:
        if "# Apply memory patch to fix issues" in line:
            skip_section = True
            continue
        elif skip_section and "apply_memory_patch()" in line:
            skip_section = False
            continue
        elif skip_section:
            continue
        
        filtered_lines.append(line)
    
    # Write the updated content
    with open("main_desktop.py", "w") as f:
        f.write("\n".join(filtered_lines))
    
    print("Successfully updated main_desktop.py to use SimpleReActAgent")

if __name__ == "__main__":
    update_main_desktop()
