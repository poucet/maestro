"""MCP server implementation for the supervisor."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from mcp.server import Server
from mcp.server.fastmcp import FastMCP

from supervisor.core import FileManager, ProcessManager, VersionControlManager
from supervisor.mcp.services import (
    register_file_services,
    register_git_services,
    register_process_services,
)

logger = logging.getLogger(__name__)


def create_mcp_server(
    process_manager: ProcessManager,
    file_manager: FileManager,
    version_control_manager: VersionControlManager,
    transport: str = "stdio",
) -> Server:
    """Create an MCP server for the supervisor.

    Args:
        process_manager: Process manager instance.
        file_manager: File manager instance.
        version_control_manager: Version control manager instance.
        transport: MCP transport type, either "stdio" or "http".

    Returns:
        Configured MCP server.
    """
    # Create FastMCP server instance
    mcp = FastMCP("supervisor")

    # Register all services
    register_process_services(mcp, process_manager)
    register_file_services(mcp, file_manager)
    register_git_services(mcp, version_control_manager)

    # Add handlers for additional capabilities as needed
    return mcp


def start_mcp_server() -> None:
    """Start the MCP server with configuration from environment variables."""
    # Get configuration from environment variables
    target_cmd = os.environ.get("SUPERVISOR_TARGET_CMD", "")
    working_dir = os.environ.get("SUPERVISOR_WORKING_DIR", ".")
    log_level = os.environ.get("SUPERVISOR_LOG_LEVEL", "INFO")

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create working directory Path
    work_dir_path = Path(working_dir).resolve()
    
    # Initialize managers
    process_manager = ProcessManager(
        ProcessManager.ProcessConfig(
            command=target_cmd,
            working_dir=work_dir_path,
        )
    )
    
    file_manager = FileManager(allowed_paths=[work_dir_path])
    
    version_control_manager = VersionControlManager(repo_path=work_dir_path)
    
    # Create and start MCP server
    mcp_server = create_mcp_server(
        process_manager=process_manager,
        file_manager=file_manager,
        version_control_manager=version_control_manager,
    )
    
    # Run the server
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    start_mcp_server()
