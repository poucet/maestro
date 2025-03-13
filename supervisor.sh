#!/bin/bash

# Supervisor Script for Simply Projects
# Monitors for code changes and automatically restarts managed processes

# Parse arguments
APP_NAME=${1:-"Simply Maestro"}
COMMAND=${2:-"uv run -m simply_maestro"}
PORT=${3:-4998}
PID_FILE=${4:-".simply_maestro.pid"}
APP_DIR=${5:-"/home/chris/projects/simply/maestro"}
RESTART_EXIT_CODE=${6:-42}

echo "$APP_NAME Supervisor starting..."
echo "--------------------------------------"
echo "Command: $COMMAND"
echo "Monitoring port: $PORT"
echo "PID file: $PID_FILE"
echo "App directory: $APP_DIR"
echo "Restart exit code: $RESTART_EXIT_CODE"

# Function to get file modification time
get_last_modified() {
  find "$APP_DIR" -type f -name "*.py" -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/__pycache__/*" -exec stat -c "%Y" {} \; | sort -nr | head -1
}

# Store initial state
LAST_MODIFIED=$(get_last_modified)
echo "Initial code state recorded."

# Function to check if port is in use
check_port_in_use() {
  local port_pid=$(lsof -ti:$PORT 2>/dev/null | tr '\n' ' ')
  if [ ! -z "$port_pid" ]; then
    echo "Port $PORT is already in use by PID $port_pid"
    return 0
  else
    return 1
  fi
}

# Function to kill any process using the port
kill_port_process() {
  # Get all PIDs using the port
  local port_pids=$(lsof -ti:$PORT 2>/dev/null)
  if [ ! -z "$port_pids" ]; then
    for pid in $port_pids; do
      echo "Killing process using port $PORT (PID: $pid)..."
      kill -TERM $pid 2>/dev/null
    done
    
    # Wait up to 5 seconds for graceful shutdown
    for i in {1..5}; do
      if ! lsof -ti:$PORT >/dev/null 2>&1; then
        echo "All processes on port $PORT terminated successfully."
        return 0
      fi
      sleep 1
    done
    
    # Force kill if necessary
    port_pids=$(lsof -ti:$PORT 2>/dev/null)
    if [ ! -z "$port_pids" ]; then
      echo "Forcing termination of processes on port $PORT..."
      for pid in $port_pids; do
        kill -9 $pid 2>/dev/null
      done
      sleep 1
    fi
  fi
}

# Function to gracefully shutdown the process
graceful_shutdown() {
  echo "Shutting down $APP_NAME..."
  if [ ! -z "$PROCESS_PID" ]; then
    kill -TERM "$PROCESS_PID" 2>/dev/null
    # Wait up to 10 seconds for graceful shutdown
    for i in {1..10}; do
      if ! kill -0 "$PROCESS_PID" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    # Force kill if necessary
    if kill -0 "$PROCESS_PID" 2>/dev/null; then
      echo "Forcing termination..."
      kill -9 "$PROCESS_PID" 2>/dev/null
    fi
  fi
}

# Handle signals
trap 'graceful_shutdown; exit 0' SIGINT SIGTERM

# Main loop
while true; do
  echo "Starting $APP_NAME..."
  cd "$APP_DIR"
  
  # Check if port is already in use
  if check_port_in_use; then
    echo "Port $PORT is already in use. Attempting to free it..."
    kill_port_process
    # Give a moment for the port to be fully released
    sleep 2
  fi
  
  # Start the process in the background
  eval $COMMAND &
  PROCESS_PID=$!
  # Store the PID for the kill script
  echo $PROCESS_PID > $PID_FILE
  echo "$APP_NAME started with PID $PROCESS_PID"
  
  # Wait for the process to exit or for code changes
  while kill -0 $PROCESS_PID 2>/dev/null; do
    CURRENT_MODIFIED=$(get_last_modified)
    
    # Check if files have been modified
    if [ "$CURRENT_MODIFIED" != "$LAST_MODIFIED" ]; then
      echo "Code changes detected. Restarting..."
      LAST_MODIFIED=$CURRENT_MODIFIED
      graceful_shutdown
      # Short pause before restart
      sleep 2
      break
    fi
    
    # Check every 5 seconds
    sleep 5
  done
  
  # If we get here without breaking, the process exited on its own
  # Get the exit code
  wait $PROCESS_PID
  EXIT_CODE=$?
  
  if [ $EXIT_CODE -eq $RESTART_EXIT_CODE ]; then
    echo "$APP_NAME requested restart (exit code $RESTART_EXIT_CODE)"
    # Continue the loop to restart
  elif [ $EXIT_CODE -ne 0 ]; then
    echo "$APP_NAME crashed with exit code $EXIT_CODE, restarting in 10 seconds..."
    sleep 10
  else
    echo "$APP_NAME exited normally with exit code $EXIT_CODE, restarting in 5 seconds..."
    sleep 5
  fi
done
