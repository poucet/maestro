# Simply Maestro

> *Orchestrating code and processes with precision and elegance*

A Python-based process manager that monitors, coordinates, and conducts the lifecycle of other processes and code. Like a maestro directing an orchestra, Simply Maestro harmonizes all aspects of your application's runtime environment through the Model Context Protocol (MCP).

Part of the "Simply" family of tools, Simply Maestro brings sophisticated process management capabilities with the simplicity and reliability you expect.

## Features

- **Process Monitoring**: Real-time monitoring of a target process
- **Process Management**: Start and restart capabilities
- **File Operations**: Reading, editing, and searching files
- **Version Control**: Git integration for code management
- **MCP Integration**: Expose capabilities through standardized MCP services

## MCP Service Capabilities

Simply Maestro exposes the following capabilities as MCP services, organized by category:

### Process Management
- `start_task` - Monitor an existing process or start a new one
- `stop_task` - Stop a running process
- `restart_task` - Emergency restart when needed (target processes typically have their own restart mechanisms)

### Process Logging
- `list_process_logs` - List available process log files
- `read_process_log` - Read the contents of a specific log file

### File Operations
- `read_file` - Read file contents
- `edit_file` - Direct file editing
- `change_in_file` - Apply diffs to files
- `search_files` - Search files with ripgrep

### Version Control (Git)
- `git_restore` - Git restore operations
- `git_commit` - Git commit operations

## Installation

Ensure you have Python 3.10+ and `uv` installed. Then:

```bash
# Clone the repository
git clone https://github.com/poucet/maestro.git
cd maestro

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
```

## Configuration

Simply Maestro requires the following environment variables:

- `SIMPLY_MAESTRO_TARGET_CMD`: Command to start the target process
- `SIMPLY_MAESTRO_WORKING_DIR`: Working directory for operations
- `SIMPLY_MAESTRO_LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `SIMPLY_MAESTRO_MCP_PORT`: Port for the MCP server (default: 4998)
- `SIMPLY_MAESTRO_TARGET_PORT`: Port for the target process (for discovery)

## Usage

```bash
# Start Simply Maestro directly
python -m simply_maestro

# Or use the provided scripts:
# Start Simply Maestro in the background with logging
./start.sh

# Stop Simply Maestro and any managed processes
./kill.sh
```

## Development

Install development dependencies:

```bash
uv pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## License

MIT
