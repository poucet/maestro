#!/bin/bash
# Unified script for controlling the simply-maestro service via supervisor.

# Get the absolute path to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to the supervisor script
SUPERVISOR_SCRIPT="$SCRIPT_DIR/../supervisor/supervisor.sh"

# Check if the supervisor script exists
if [ ! -f "$SUPERVISOR_SCRIPT" ]; then
    echo "Error: Supervisor script not found at $SUPERVISOR_SCRIPT"
    echo "Please ensure the supervisor repository is cloned at the same level as the maestro repository."
    exit 1
fi

# Get the subcommand
SUBCOMMAND=$1
shift

# Call the supervisor's command
case "$SUBCOMMAND" in
    start|stop|restart|status|logs)
        "$SUPERVISOR_SCRIPT" "$SUBCOMMAND" "$@"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs} [options]"
        exit 1
        ;;
esac
