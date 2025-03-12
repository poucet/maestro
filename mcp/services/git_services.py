"""MCP services for Git operations."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from mcp.server.fastmcp import FastMCP

from supervisor.core import VersionControlManager

logger = logging.getLogger(__name__)


def register_git_services(mcp: FastMCP, version_control_manager: VersionControlManager) -> None:
    """Register Git operation MCP services.

    Args:
        mcp: MCP server instance.
        version_control_manager: Version control manager instance.
    """
    
    @mcp.tool()
    async def git_commit(message: str, files: Optional[List[str]] = None) -> str:
        """Commit changes to the Git repository.
        
        Args:
            message: Commit message.
            files: Optional list of files to commit. If None, commits all changes.
            
        Returns:
            A message indicating success or failure.
        """
        file_paths = [Path(f) for f in files] if files else None
        success, result = version_control_manager.commit(message, file_paths)
        if not success:
            logger.error(f"Failed to commit changes: {result}")
            return f"Error: {result}"
        return result

    @mcp.tool()
    async def git_restore(files: List[str], staged: bool = False) -> str:
        """Restore files to their state in the last commit.
        
        Args:
            files: List of files to restore.
            staged: If True, restore files from the staging area.
            
        Returns:
            A message indicating success or failure.
        """
        file_paths = [Path(f) for f in files]
        success, message = version_control_manager.restore(file_paths, staged)
        if not success:
            logger.error(f"Failed to restore files: {message}")
            return f"Error: {message}"
        return message
