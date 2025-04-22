"""
Box drawing utilities for CPAS3
Provides ASCII/Unicode box-drawing functions for terminal-style UIs
"""

def draw_simple_box(width: int, height: int, title: str = "", content: str = "") -> str:
    """
    Draw a simple box with single-line borders
    
    Args:
        width: Width of the box in characters
        height: Height of the box in rows
        title: Optional title to display at the top
        content: Optional content to display in the box
    
    Returns:
        String representation of the box
    """
    # Ensure minimum dimensions
    width = max(width, 10)
    height = max(height, 3)
    
    # Prepare lines
    lines = []
    
    # Top border with title
    if title:
        title_padding = max(0, (width - 4 - len(title)) // 2)
        top_border = "┌" + "─" * title_padding + "┤ " + title + " ├" + "─" * (width - 4 - len(title) - title_padding) + "┐"
    else:
        top_border = "┌" + "─" * (width - 2) + "┐"
    lines.append(top_border)
    
    # Content lines
    content_lines = content.split("\n") if content else []
    
    # Calculate available space for content
    content_height = height - 2  # Subtract top and bottom borders
    
    # If we have more content lines than space, truncate
    if len(content_lines) > content_height:
        content_lines = content_lines[:content_height-1] + ["..."]
    
    # Add empty lines if content is shorter than available space
    while len(content_lines) < content_height:
        content_lines.append("")
    
    # Add content lines with borders
    for line in content_lines:
        # Truncate or pad line to fit width
        if len(line) > width - 4:
            line = line[:width - 7] + "..."
        else:
            line = line + " " * (width - 4 - len(line))
        
        lines.append("│ " + line + " │")
    
    # Bottom border
    bottom_border = "└" + "─" * (width - 2) + "┘"
    lines.append(bottom_border)
    
    return "\n".join(lines)

def draw_double_box(width: int, height: int, title: str = "", content: str = "") -> str:
    """
    Draw a box with double-line borders
    
    Args:
        width: Width of the box in characters
        height: Height of the box in rows
        title: Optional title to display at the top
        content: Optional content to display in the box
    
    Returns:
        String representation of the box
    """
    # Ensure minimum dimensions
    width = max(width, 10)
    height = max(height, 3)
    
    # Prepare lines
    lines = []
    
    # Top border with title
    if title:
        title_padding = max(0, (width - 4 - len(title)) // 2)
        top_border = "╔" + "═" * title_padding + "╡ " + title + " ╞" + "═" * (width - 4 - len(title) - title_padding) + "╗"
    else:
        top_border = "╔" + "═" * (width - 2) + "╗"
    lines.append(top_border)
    
    # Content lines
    content_lines = content.split("\n") if content else []
    
    # Calculate available space for content
    content_height = height - 2  # Subtract top and bottom borders
    
    # If we have more content lines than space, truncate
    if len(content_lines) > content_height:
        content_lines = content_lines[:content_height-1] + ["..."]
    
    # Add empty lines if content is shorter than available space
    while len(content_lines) < content_height:
        content_lines.append("")
    
    # Add content lines with borders
    for line in content_lines:
        # Truncate or pad line to fit width
        if len(line) > width - 4:
            line = line[:width - 7] + "..."
        else:
            line = line + " " * (width - 4 - len(line))
        
        lines.append("║ " + line + " ║")
    
    # Bottom border
    bottom_border = "╚" + "═" * (width - 2) + "╝"
    lines.append(bottom_border)
    
    return "\n".join(lines)

def draw_nested_box_layout(width: int, height: int) -> str:
    """
    Create a complex nested box layout demonstration
    
    Args:
        width: Overall width
        height: Overall height
    
    Returns:
        String representation of the nested box layout
    """
    # Ensure minimum dimensions
    width = max(width, 40)
    height = max(height, 15)
    
    # Build the layout string
    lines = []
    
    # Top border of outer box
    lines.append("┌" + "─" * (width - 2) + "┐")
    
    # Content area
    content_height = height - 2
    inner_width = width - 4
    
    # Top section (about 1/3 of the content area)
    top_section_height = max(3, content_height // 3)
    
    # Add a few empty lines
    for _ in range(1):
        lines.append("│ " + " " * inner_width + " │")
    
    # Add inner box in top section
    inner_box = draw_simple_box(inner_width - 4, top_section_height - 2, "Agent Status", "● Agent 1: Running\n● Agent 2: Idle\n● Agent 3: Stopped").split("\n")
    for line in inner_box:
        lines.append("│  " + line + "  │")
    
    # Add a few empty lines
    for _ in range(1):
        lines.append("│ " + " " * inner_width + " │")
    
    # Divider
    lines.append("├" + "─" * inner_width + "┤")
    
    # Bottom section (remaining space)
    bottom_section_height = content_height - top_section_height - 3  # -3 for the empty lines and divider
    
    # Split bottom section into two columns
    col_width = (inner_width - 3) // 2  # -3 for the divider and padding
    
    # Left column - Agent Controls
    left_box = draw_simple_box(col_width, bottom_section_height - 2, "Controls", "→ Create Agent\n→ Configure\n→ Start/Stop\n→ Delete").split("\n")
    
    # Right column - Agent Details
    right_box = draw_simple_box(col_width, bottom_section_height - 2, "Details", "Name: Test Agent\nType: Task Agent\nStatus: Running\nCPU: 12%\nMem: 45 MB").split("\n")
    
    # Add a line of spacing
    lines.append("│ " + " " * inner_width + " │")
    
    # Combine the columns side by side
    for i in range(max(len(left_box), len(right_box))):
        left_line = left_box[i] if i < len(left_box) else " " * col_width
        right_line = right_box[i] if i < len(right_box) else " " * col_width
        lines.append("│ " + left_line + " │ " + right_line + " │")
    
    # Add a line of spacing
    lines.append("│ " + " " * inner_width + " │")
    
    # Bottom border of outer box
    lines.append("└" + "─" * (width - 2) + "┘")
    
    return "\n".join(lines)
