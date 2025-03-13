#!/bin/bash

# Kill script for Simply Projects
# Stops both the supervisor and the managed process

# Configuration - should match start.sh
APP_NAME="Simply Maestro"
PID_FILE=".simply_maestro.pid"
SUPERVISOR_PID_FILE=".supervisor.pid"

echo "Stopping $APP_NAME and its supervisor..."

# Function to kill a process by PID
kill_process_by_pid() {
    local pid=$1
    local signal=$2
    local process_name=$3

    if ps -p $pid > /dev/null 2>&1; then
        echo "Sending $signal signal to $process_name (PID: $pid)..."
        kill -$signal $pid
        return 0
    else
        echo "$process_name process with PID $pid is not running."
        return 1
    fi
}

# Check and kill managed process
if [ -f $PID_FILE ]; then
    PROCESS_PID=$(cat $PID_FILE)
    kill_process_by_pid $PROCESS_PID TERM "$APP_NAME"
    # Remove the PID file
    rm $PID_FILE
else
    echo "$APP_NAME PID file not found."
fi

# Check and kill supervisor process
if [ -f $SUPERVISOR_PID_FILE ]; then
    SUPERVISOR_PID=$(cat $SUPERVISOR_PID_FILE)
    kill_process_by_pid $SUPERVISOR_PID TERM "Supervisor"
    # Remove the PID file
    rm $SUPERVISOR_PID_FILE
else
    echo "Supervisor PID file not found."
fi

# Wait a moment to give processes time to exit gracefully
sleep 2

# Check if processes are still running
still_running=false

# Check managed process if PID was found
if [ -n "$PROCESS_PID" ] && ps -p $PROCESS_PID > /dev/null 2>&1; then
    echo "$APP_NAME process (PID: $PROCESS_PID) is still running."
    still_running=true
fi

# Check supervisor process if PID was found
if [ -n "$SUPERVISOR_PID" ] && ps -p $SUPERVISOR_PID > /dev/null 2>&1; then
    echo "Supervisor process (PID: $SUPERVISOR_PID) is still running."
    still_running=true
fi

# Force kill if processes are still running
if $still_running; then
    echo "Some processes are still running. Force kill? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Force killing remaining processes..."

        # Force kill managed process if still running
        if [ -n "$PROCESS_PID" ] && ps -p $PROCESS_PID > /dev/null 2>&1; then
            kill_process_by_pid $PROCESS_PID 9 "$APP_NAME"
        fi

        # Force kill supervisor if still running
        if [ -n "$SUPERVISOR_PID" ] && ps -p $SUPERVISOR_PID > /dev/null 2>&1; then
            kill_process_by_pid $SUPERVISOR_PID 9 "Supervisor"
        fi

        echo "All processes have been forcefully terminated."
    else
        echo "Abort. Some processes may still be running."
        exit 1
    fi
fi

echo "$APP_NAME shutdown complete."
