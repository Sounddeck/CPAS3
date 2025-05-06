"""
Patch for main_desktop.py to fix memory issues
Run this script before running the main application
"""

import os
import sys

def create_patched_main():
    """
    Create a patched version of main_desktop.py
    """
    # Read the original main_desktop.py
    with open("main_desktop.py", "r") as f:
        lines = f.readlines()
    
    # Find the position to insert the patch - after the local imports
    position = 0
    for i, line in enumerate(lines):
        if "# Local imports" in line:
            # Find the end of the imports section
            for j in range(i+1, len(lines)):
                if not lines[j].strip() or lines[j].startswith("#"):
                    position = j
                    break
            break
    
    # Insert the patch code
    patch_code = [
        "\n",
        "# Apply memory patch to fix issues\n",
        "from src.agents.react_agent_memory_fix import apply_memory_patch\n",
        "apply_memory_patch()\n",
        "\n"
    ]
    
    patched_lines = lines[:position] + patch_code + lines[position:]
    
    # Write the patched file
    with open("main_desktop.py", "w") as f:
        f.writelines(patched_lines)
    
    print("Successfully patched main_desktop.py to fix memory issues")

if __name__ == "__main__":
    create_patched_main()
