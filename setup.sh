#!/bin/bash
# Setup script for CPAS Desktop

# Determine the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=== Setting up CPAS Desktop Environment ==="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not found."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        exit 1
    fi
fi

# Activate virtual environment
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment."
    exit 1
fi

# Install required packages
echo "Installing required packages..."
pip install --upgrade pip
pip install PyQt6

# Create required directories if they don't exist
echo "Setting up directory structure..."
mkdir -p data/agents

echo ""
echo "=== Setup Complete ==="
echo "To run CPAS Desktop, use: ./run_cpas.sh"
echo ""

# Make the run script executable
chmod +x run_cpas.sh

exit 0
