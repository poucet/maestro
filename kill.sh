#!/bin/bash

# Kill script for Simply Maestro
# Delegates to the shared supervisor kill script

# Use shared supervisor directory
SUPERVISOR_DIR="../supervisor"

# Check if configuration file exists
if [ ! -f ".supervisor" ]; then
    echo "Error: .supervisor configuration file not found!"
    exit 1
fi

# Check if supervisor directory exists
if [ ! -d "$SUPERVISOR_DIR" ]; then
    echo "Error: Supervisor directory not found at $SUPERVISOR_DIR"
    exit 1
fi

# Check if kill script exists
if [ ! -f "$SUPERVISOR_DIR/kill.sh" ]; then
    echo "Error: kill.sh not found in $SUPERVISOR_DIR"
    exit 1
fi

# Execute the shared kill script with our configuration
echo "Using shared kill script..."
CURRENT_DIR=$(pwd)
"$SUPERVISOR_DIR/kill.sh" "conf=$CURRENT_DIR/.supervisor"
