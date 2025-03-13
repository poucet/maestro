"""MCP server implementation for Simply Maestro."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from simply_maestro.core import FileManager, VersionControlManager
from simply_maestro.core.process_manager import ProcessManager, ProcessConfig
from simply_maestro.mcp.services import (
    register_file_services,
    register_git_services,
    register_process_services,
)

logger = logging.getLogger(__name__)


def create_mcp_server(
    process_manager: ProcessManager,
    file_manager: FileManager,
    version_control_manager: VersionControlManager,
    mcp_port: int
) -> FastMCP:
    """Create an MCP server for Simply Maestro.

    Args:
        process_manager: Process manager instance.
        file_manager: File manager instance.
        version_control_manager: Version control manager instance.

    Returns:
        Configured MCP server.
    """
    # Create FastMCP server instance
    mcp = FastMCP("simply-maestro", host="0.0.0.0", port=mcp_port)

    # Register all services
    register_process_services(mcp, process_manager)
    register_file_services(mcp, file_manager)
    register_git_services(mcp, version_control_manager)

    # Add handlers for additional capabilities as needed
    return mcp


def start_mcp_server() -> None:
    """Start the MCP server with configuration from environment variables."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get configuration from environment variables
    target_cmd = os.environ.get("SIMPLY_MAESTRO_TARGET_CMD", "")
    working_dir = os.environ.get("SIMPLY_MAESTRO_WORKING_DIR", ".")
    log_level = os.environ.get("SIMPLY_MAESTRO_LOG_LEVEL", "INFO")
    mcp_port = int(os.environ.get("SIMPLY_MAESTRO_MCP_PORT", "5000"))
    target_port = os.environ.get("SIMPLY_MAESTRO_TARGET_PORT")
    if target_port:
        target_port = int(target_port)
    else:
        target_port = 5000  # Default port for simplicity

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logger.info(f"Starting Simply Maestro with target command: {target_cmd}")
    logger.info(f"Working directory: {working_dir}")
    logger.info(f"Log level: {log_level}")
    logger.info(f"MCP server port: {mcp_port}")

    # Create working directory Path
    work_dir_path = Path(working_dir).resolve()
    
    # Initialize managers
    process_manager = ProcessManager(
        ProcessConfig(
            command=target_cmd,
            working_dir=work_dir_path,
            port=target_port,  # Pass the target port for process discovery
        )
    )
    
    # Log if we're watching for a port
    if target_port:
        logger.info(f"Monitoring for processes on port: {target_port}")
    
    # Change working directory to match the target process
    logger.info(f"Changing working directory to: {work_dir_path}")
    try:
        os.chdir(work_dir_path)
        logger.info(f"Current working directory is now: {os.getcwd()}")
    except Exception as e:
        logger.error(f"Failed to change working directory: {str(e)}")
    
    file_manager = FileManager(allowed_paths=[work_dir_path])
    
    version_control_manager = VersionControlManager(repo_path=work_dir_path)
    
    # Create MCP server
    mcp_server = create_mcp_server(
        process_manager=process_manager,
        file_manager=file_manager,
        version_control_manager=version_control_manager,
        mcp_port=mcp_port
    )
    mcp_server.run("sse")

if __name__ == "__main__":
    start_mcp_server()
