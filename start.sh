#!/bin/bash

# Start script for Simply Maestro
# Simple wrapper that delegates to the shared supervisor start script

# Configuration
SUPERVISOR_DIR="../supervisor"
CONFIG_FILE=".supervisor"
LOG_FILE="supervisor.log"

# Quick error checks
[ ! -d "$SUPERVISOR_DIR" ] && echo "Error: Supervisor directory not found at $SUPERVISOR_DIR" && exit 1
[ ! -f "$SUPERVISOR_DIR/start.sh" ] && echo "Error: start.sh not found in $SUPERVISOR_DIR" && exit 1
[ ! -f "$CONFIG_FILE" ] && echo "Error: $CONFIG_FILE not found!" && exit 1

# Execute the shared start script with our configuration
echo "Using shared start script from $SUPERVISOR_DIR..."
CURRENT_DIR=$(pwd)

# Use absolute paths for both configuration and log files
cd "$SUPERVISOR_DIR"
./start.sh "conf=$CURRENT_DIR/$CONFIG_FILE" "log=$CURRENT_DIR/$LOG_FILE"
cd - > /dev/null
