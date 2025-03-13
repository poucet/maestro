#!/bin/bash

# Start script for Simply Maestro
# Launches the supervisor in the background with logging

echo "Starting Simply Maestro supervisor..."
nohup ./supervisor.sh > supervisor.log 2>&1 &

# Get the PID of the supervisor process
SUPERVISOR_PID=$!

# Store the supervisor PID to a file
echo $SUPERVISOR_PID > .supervisor.pid
echo "Supervisor PID $SUPERVISOR_PID saved to .supervisor.pid"

echo "Simply Maestro supervisor started with PID $SUPERVISOR_PID"
echo "Logs are being written to supervisor.log"
echo "Use ./kill.sh to stop the supervisor and its managed processes"
