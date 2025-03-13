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

The following capabilities are exposed as MCP services:

1. `restart_task` - Restart a running server
2. `start_task` - Start a server process
3. `read_file` - Read file contents
4. `edit_file` - Direct file editing
5. `change_in_file` - Apply diffs to files
6. `search_files` - Search files with ripgrep
7. `git_restore` - Git restore operations
8. `git_commit` - Git commit operations

## Installation

Ensure you have Python 3.10+ and `uv` installed. Then:

```bash
# Clone the repository
git clone https://github.com/username/simply-maestro.git
cd simply-maestro

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
- `SIMPLY_MAESTRO_MCP_PORT`: Port for the MCP server (default: 5000)
- `SIMPLY_MAESTRO_TARGET_PORT`: Port for the target process (for discovery)

## Usage

```bash
# Start Simply Maestro
python -m simply_maestro
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
