#!/usr/bin/env python3
"""
Box drawing example for CPAS3
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the box drawing functions
from modules.ui.box_drawing import draw_box, draw_box_with_double_border

# Simple example of a box
print("\n=== Simple Box ===\n")
print(draw_box(40, 5, "Simple Box", "This is a simple box example."))
print()

# Example with double border
print("\n=== Double Border Box ===\n")
print(draw_box_with_double_border(40, 5, "Double Border", "This box has a double-line border."))
print()

# Example with multiple lines
print("\n=== Multi-line Box ===\n")
content = "Line 1\nLine 2\nLine 3\nLine 4"
print(draw_box(40, 7, "Multi-line Content", content))
