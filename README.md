# Python Supervisor Process

A Python-based supervisor process that can monitor, edit code, and manage the lifecycle of another process. This system is integrated with the Model Context Protocol (MCP) to expose its capabilities as services.

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
git clone https://github.com/username/supervisor.git
cd supervisor

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
```

## Configuration

The supervisor requires the following environment variables:

- `SUPERVISOR_TARGET_CMD`: Command to start the target process
- `SUPERVISOR_WORKING_DIR`: Working directory for operations
- `SUPERVISOR_LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

## Usage

```bash
# Start the supervisor
python -m supervisor
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
