#!/bin/bash

# Kill script for Simply Maestro
# Simple wrapper that delegates to the shared supervisor kill script

# Configuration
SUPERVISOR_DIR="../supervisor"
CONFIG_FILE=".supervisor"

# Quick error checks
[ ! -d "$SUPERVISOR_DIR" ] && echo "Error: Supervisor directory not found at $SUPERVISOR_DIR" && exit 1
[ ! -f "$SUPERVISOR_DIR/kill.sh" ] && echo "Error: kill.sh not found in $SUPERVISOR_DIR" && exit 1
[ ! -f "$CONFIG_FILE" ] && echo "Error: $CONFIG_FILE not found!" && exit 1

# Execute the shared kill script with our configuration
echo "Using shared kill script..."
CURRENT_DIR=$(pwd)
"$SUPERVISOR_DIR/kill.sh" "conf=$CURRENT_DIR/$CONFIG_FILE"
