#!/bin/bash

# CPAS3 Application Launcher

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the application
echo "Starting CPAS3..."
python run_cpas.py

# Exit status
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "CPAS3 exited with error code: $exit_code"
    exit $exit_code
fi
