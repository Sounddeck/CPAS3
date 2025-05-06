#!/bin/bash
# CPAS3 Launcher Script

# Ensure we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if Ollama is running
echo "Checking if Ollama is running..."
curl -s http://localhost:11434/api/version > /dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ Ollama doesn't appear to be running. Start it before continuing."
    echo "You can start Ollama with the 'ollama serve' command in another terminal."
    read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
fi

# Check for required model
echo "Checking for required model..."
REQUIRED_MODEL="llama3"
curl -s "http://localhost:11434/api/tags" | grep -q "\"name\":\"$REQUIRED_MODEL\""
if [ $? -ne 0 ]; then
    echo "⚠️ Required model '$REQUIRED_MODEL' not found in Ollama."
    echo "You can download it with: ollama pull $REQUIRED_MODEL"
    read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
fi

# Run the application
echo "Starting CPAS3..."
python main_desktop.py

# Deactivate virtual environment when done
if [ -d "venv" ]; then
    deactivate
fi
