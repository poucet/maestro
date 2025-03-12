# Tech Context: Python Supervisor Process

## Technologies Used

### Core Technologies

1. **Python 3.10+**: The primary implementation language, chosen for its robust standard library, process management capabilities, and wide adoption
2. **Model Context Protocol (MCP)**: The protocol for exposing supervisor capabilities as standardized services
3. **Git**: Version control system integrated for code management

### Libraries and Frameworks

1. **subprocess**: Python standard library module for spawning and managing processes
2. **psutil**: Third-party library for process and system monitoring
3. **asyncio**: For asynchronous operation handling
4. **pathlib**: Modern file system path handling
5. **difflib**: For handling file differences
6. **fastapi/starlette**: For HTTP-based MCP server implementation (optional)

### Development Tools

1. **pytest**: For unit and integration testing
2. **black**: For code formatting
3. **ruff**: For linting and static code analysis
4. **mypy**: For static type checking
5. **ripgrep**: For efficient file searching

## Development Setup

### Environment

The development environment requires:

1. Python 3.10 or higher
2. Git
3. Virtual environment management (venv, poetry, or similar)
4. ripgrep installed on the system

### Configuration

The supervisor process requires configuration for:

1. Target process settings (command, arguments, working directory)
2. File system boundaries for operations
3. MCP service setup (endpoints, permissions)
4. Logging and monitoring preferences

### Project Structure

```
supervisor/
├── core/
│   ├── __init__.py
│   ├── process_manager.py  # Process management functionality
│   ├── file_manager.py     # File operations
│   └── version_control.py  # Git operations
├── mcp/
│   ├── __init__.py
│   ├── server.py           # MCP server implementation
│   └── services/           # Individual MCP service implementations
│       ├── __init__.py
│       ├── process_services.py
│       ├── file_services.py
│       └── git_services.py
├── utils/
│   ├── __init__.py
│   ├── logging.py          # Logging utilities
│   └── security.py         # Security helpers
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_process_manager.py
│   ├── test_file_manager.py
│   └── test_mcp_services.py
├── pyproject.toml          # Project metadata and dependencies
├── README.md               # Project documentation
└── supervisor.py           # Main entry point
```

## Technical Constraints

### Platform Compatibility

- Designed primarily for Linux and macOS environments
- Windows support may have limitations, especially for process management

### Performance Considerations

1. **Minimal Overhead**: The supervisor should have minimal impact on the target process's performance
2. **Resource Usage**: Efficient resource usage to ensure the supervisor doesn't compete with the target process
3. **Scalability**: Should handle moderate-sized codebases and process loads effectively

### Security Boundaries

1. **File System Access**: Limited to specified directories
2. **Process Control**: Limited to authorized processes
3. **Command Execution**: Restricted command execution with proper validation

## Dependencies

### External Dependencies

1. **Python Runtime**: Python 3.10+
2. **Git**: For version control operations
3. **ripgrep**: For efficient file searching

### Python Package Dependencies

1. **Core Dependencies**:
   - psutil>=5.9.0
   - asyncio (stdlib)
   - pathlib (stdlib)
   - difflib (stdlib)
   - subprocess (stdlib)

2. **MCP Protocol Implementation**:
   - mcp-python>=1.0.0 (or custom implementation)
   - fastapi>=0.95.0 (if using HTTP transport)
   - uvicorn>=0.22.0 (if using HTTP transport)

3. **Development Dependencies**:
   - pytest>=7.3.1
   - black>=23.3.0
   - ruff>=0.0.261
   - mypy>=1.2.0

## Deployment Considerations

### Packaging

The supervisor should be packaged as a Python package installable via pip.

### Environment Variables

Required environment variables include:
- `SUPERVISOR_TARGET_CMD`: Command to start the target process
- `SUPERVISOR_WORKING_DIR`: Working directory for operations
- `SUPERVISOR_LOG_LEVEL`: Logging verbosity

### Process Lifecycle

The supervisor should be started before the target process and should handle graceful shutdown of the target process when the supervisor itself is shut down.

## Technical Debt and Limitations

1. **Process Handling Complexity**: Process monitoring and management can be complex and may not cover all edge cases initially
2. **Cross-Platform Limitations**: Some functionality may be platform-specific
3. **Git Integration Edge Cases**: Complex Git operations may not be fully supported in early versions
4. **Error Recovery**: Sophisticated error recovery mechanisms may need to evolve over time

## Monitoring and Observability

1. **Logging**: Comprehensive logging of all operations and errors
2. **Metrics**: Basic metrics for process health and operation counts
3. **Status Endpoint**: An endpoint for checking the supervisor's own status
