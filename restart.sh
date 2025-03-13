#!/bin/bash

# Restart script for Simply Maestro
# Simple wrapper that delegates to the shared supervisor restart script

# Configuration
SUPERVISOR_DIR="../supervisor"
CONFIG_FILE=".supervisor"

# Quick error checks
[ ! -d "$SUPERVISOR_DIR" ] && echo "Error: Supervisor directory not found at $SUPERVISOR_DIR" && exit 1
[ ! -f "$SUPERVISOR_DIR/restart.sh" ] && echo "Error: restart.sh not found in $SUPERVISOR_DIR" && exit 1
[ ! -f "$CONFIG_FILE" ] && echo "Error: $CONFIG_FILE not found!" && exit 1

# Execute the shared restart script with our configuration
echo "Using shared restart script..."
CURRENT_DIR=$(pwd)
"$SUPERVISOR_DIR/restart.sh" "conf=$CURRENT_DIR/$CONFIG_FILE"
