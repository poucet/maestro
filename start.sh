#!/bin/bash

# Start script for Simply Maestro
# Launches the supervisor in the background with logging

# Configuration
APP_NAME="Simply Maestro"
COMMAND="uv run -m simply_maestro"
PORT=4998
PID_FILE=".simply_maestro.pid"
APP_DIR="/home/chris/projects/simply/maestro"
RESTART_EXIT_CODE=42
SUPERVISOR_PID_FILE=".supervisor.pid"

# Check if supervisor is already running
if [ -f "$SUPERVISOR_PID_FILE" ]; then
  EXISTING_PID=$(cat "$SUPERVISOR_PID_FILE")
  if ps -p "$EXISTING_PID" > /dev/null; then
    echo "Supervisor is already running with PID $EXISTING_PID"
    echo "Use ./kill.sh to stop it before starting a new one"
    exit 1
  else
    echo "Removing stale PID file for non-existent process $EXISTING_PID"
    rm "$SUPERVISOR_PID_FILE"
  fi
fi

echo "Starting $APP_NAME supervisor..."
nohup ./supervisor.sh "$APP_NAME" "$COMMAND" "$PORT" "$PID_FILE" "$APP_DIR" "$RESTART_EXIT_CODE" > supervisor.log 2>&1 &

# Get the PID of the supervisor process
SUPERVISOR_PID=$!

# Store the supervisor PID to a file
echo $SUPERVISOR_PID > "$SUPERVISOR_PID_FILE"
echo "Supervisor PID $SUPERVISOR_PID saved to $SUPERVISOR_PID_FILE"

echo "$APP_NAME supervisor started with PID $SUPERVISOR_PID"
echo "Logs are being written to supervisor.log"
echo "Use ./kill.sh to stop the supervisor and its managed processes"
