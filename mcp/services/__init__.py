"""MCP service implementations for the supervisor."""

from supervisor.mcp.services.file_services import register_file_services
from supervisor.mcp.services.git_services import register_git_services
from supervisor.mcp.services.process_services import register_process_services

__all__ = [
    "register_file_services",
    "register_git_services",
    "register_process_services",
]
