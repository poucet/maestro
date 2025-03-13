#!/bin/bash

# Simply Maestro Supervisor Script
# Monitors for code changes and automatically restarts the process manager

echo "Simply Maestro Supervisor starting..."
echo "--------------------------------------"

# Default directory to monitor
APP_DIR="/home/chris/projects/prime/simply-maestro"
RESTART_EXIT_CODE=42

# Function to get file modification time
get_last_modified() {
  find "$APP_DIR" -type f -name "*.py" -not -path "*/\.*" -not -path "*/venv/*" -not -path "*/__pycache__/*" -exec stat -c "%Y" {} \; | sort -nr | head -1
}

# Store initial state
LAST_MODIFIED=$(get_last_modified)
echo "Initial code state recorded."

# Function to check if port 4998 is in use
check_port_in_use() {
  local port_pid=$(lsof -t -i:4998 2>/dev/null)
  if [ ! -z "$port_pid" ]; then
    echo "Port 4998 is already in use by PID $port_pid"
    return 0
  else
    return 1
  fi
}

# Function to kill any process using port 4998
kill_port_process() {
  local port_pid=$(lsof -t -i:4998 2>/dev/null)
  if [ ! -z "$port_pid" ]; then
    echo "Killing process using port 4998 (PID $port_pid)..."
    kill -TERM "$port_pid" 2>/dev/null
    # Wait up to 5 seconds for graceful shutdown
    for i in {1..5}; do
      if ! lsof -t -i:4998 >/dev/null 2>&1; then
        echo "Process on port 4998 terminated successfully."
        return 0
      fi
      sleep 1
    done
    # Force kill if necessary
    if lsof -t -i:4998 >/dev/null 2>&1; then
      echo "Forcing termination of process on port 4998..."
      kill -9 "$port_pid" 2>/dev/null
      sleep 1
    fi
  fi
}

# Function to gracefully shutdown the process
graceful_shutdown() {
  echo "Shutting down Simply Maestro..."
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
  echo "Starting Simply Maestro..."
  cd "$APP_DIR"
  
  # Check if port 4998 is already in use
  if check_port_in_use; then
    echo "Port 4998 is already in use. Attempting to free it..."
    kill_port_process
    # Give a moment for the port to be fully released
    sleep 2
  fi
  
  # Start the process in the background
  uv run -m simply_maestro &
  PROCESS_PID=$!
  # Store the PID for the kill script
  echo $PROCESS_PID > .simply_maestro.pid
  echo "Simply Maestro started with PID $PROCESS_PID"
  
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
    echo "Process requested restart (exit code $RESTART_EXIT_CODE)"
    # Continue the loop to restart
  elif [ $EXIT_CODE -ne 0 ]; then
    echo "Process crashed with exit code $EXIT_CODE, restarting in 10 seconds..."
    sleep 10
  else
    echo "Process exited normally with exit code $EXIT_CODE, restarting in 5 seconds..."
    sleep 5
  fi
done
