#!/bin/bash

# Kill script for Simply Maestro
# Stops both the supervisor and the managed Simply Maestro process

echo "Stopping Simply Maestro and its supervisor..."

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

# Check and kill Simply Maestro process
if [ -f .simply_maestro.pid ]; then
    MAESTRO_PID=$(cat .simply_maestro.pid)
    kill_process_by_pid $MAESTRO_PID TERM "Simply Maestro"
    # Remove the PID file
    rm .simply_maestro.pid
else
    echo "Simply Maestro PID file not found."
fi

# Check and kill supervisor process
if [ -f .supervisor.pid ]; then
    SUPERVISOR_PID=$(cat .supervisor.pid)
    kill_process_by_pid $SUPERVISOR_PID TERM "Supervisor"
    # Remove the PID file
    rm .supervisor.pid
else
    echo "Supervisor PID file not found."
fi

# Wait a moment to give processes time to exit gracefully
sleep 2

# Check if processes are still running
still_running=false

# Check Simply Maestro process if PID was found
if [ -n "$MAESTRO_PID" ] && ps -p $MAESTRO_PID > /dev/null 2>&1; then
    echo "Simply Maestro process (PID: $MAESTRO_PID) is still running."
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
        
        # Force kill Simply Maestro if still running
        if [ -n "$MAESTRO_PID" ] && ps -p $MAESTRO_PID > /dev/null 2>&1; then
            kill_process_by_pid $MAESTRO_PID 9 "Simply Maestro"
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

echo "Simply Maestro shutdown complete."
