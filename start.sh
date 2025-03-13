#!/bin/bash

# Start script for Simply Maestro
# Delegates to the shared supervisor start script

# Use shared supervisor directory
SUPERVISOR_DIR="../supervisor"

# Check if supervisor directory exists
if [ ! -d "$SUPERVISOR_DIR" ]; then
    echo "Error: Supervisor directory not found at $SUPERVISOR_DIR"
    exit 1
fi

# Check if start script exists
if [ ! -f "$SUPERVISOR_DIR/start.sh" ]; then
    echo "Error: start.sh not found in $SUPERVISOR_DIR"
    exit 1
fi

# Check if configuration file exists
if [ ! -f ".supervisor" ]; then
    echo "Error: .supervisor configuration file not found!"
    exit 1
fi

# Execute the shared start script with our configuration
echo "Using shared start script from $SUPERVISOR_DIR..."
CURRENT_DIR=$(pwd)
cd "$SUPERVISOR_DIR" && ./start.sh "conf=$CURRENT_DIR/.supervisor" && cd - > /dev/null
