"""MCP server implementation for the supervisor."""

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

from supervisor.core import FileManager, VersionControlManager
from supervisor.core.process_manager import ProcessManager, ProcessConfig
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
) -> FastMCP:
    """Create an MCP server for the supervisor.

    Args:
        process_manager: Process manager instance.
        file_manager: File manager instance.
        version_control_manager: Version control manager instance.

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


async def handle_sse(request: Request):
    """Handle SSE connections."""
    sse = request.app.state.sse
    mcp_server = request.app.state.mcp_server
    
    logger.info("New SSE connection")
    
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        read_stream, write_stream = streams
        await mcp_server.run(read_stream, write_stream)


def start_mcp_server() -> None:
    """Start the MCP server with configuration from environment variables."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get configuration from environment variables
    target_cmd = os.environ.get("SUPERVISOR_TARGET_CMD", "")
    working_dir = os.environ.get("SUPERVISOR_WORKING_DIR", ".")
    log_level = os.environ.get("SUPERVISOR_LOG_LEVEL", "INFO")
    mcp_port = int(os.environ.get("SUPERVISOR_MCP_PORT", "5000"))

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logger.info(f"Starting supervisor with target command: {target_cmd}")
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
        )
    )
    
    file_manager = FileManager(allowed_paths=[work_dir_path])
    
    version_control_manager = VersionControlManager(repo_path=work_dir_path)
    
    # Create MCP server
    mcp_server = create_mcp_server(
        process_manager=process_manager,
        file_manager=file_manager,
        version_control_manager=version_control_manager,
    )
    
    # Create SSE transport and Starlette app
    sse = SseServerTransport("/messages/")
    
    routes = [
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ]
    
    app = Starlette(routes=routes)
    app.state.sse = sse
    app.state.mcp_server = mcp_server
    
    # Run the server with SSE transport
    logger.info(f"Starting MCP server with SSE on port {mcp_port}")
    uvicorn.run(app, host="0.0.0.0", port=mcp_port)


if __name__ == "__main__":
    start_mcp_server()
