"""MCP services for process management."""

import logging
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP

from supervisor.core import ProcessManager

logger = logging.getLogger(__name__)


def register_process_services(mcp: FastMCP, process_manager: ProcessManager) -> None:
    """Register process management MCP services.

    Args:
        mcp: MCP server instance.
        process_manager: Process manager instance.
    """
    
    @mcp.tool()
    async def start_task() -> str:
        """Start the managed process.
        
        Returns:
            A message indicating success or failure.
        """
        success, message = await process_manager.start()
        if not success:
            logger.error(f"Failed to start process: {message}")
            return f"Error: {message}"
        return message

    @mcp.tool()
    async def restart_task() -> str:
        """Restart the managed process.
        
        Returns:
            A message indicating success or failure.
        """
        success, message = await process_manager.restart()
        if not success:
            logger.error(f"Failed to restart process: {message}")
            return f"Error: {message}"
        return message
