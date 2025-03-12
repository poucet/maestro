"""MCP services for file operations."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from mcp.server.fastmcp import FastMCP

from supervisor.core import FileManager

logger = logging.getLogger(__name__)


def register_file_services(mcp: FastMCP, file_manager: FileManager) -> None:
    """Register file operation MCP services.

    Args:
        mcp: MCP server instance.
        file_manager: File manager instance.
    """
    
    @mcp.tool()
    async def read_file(path: str) -> str:
        """Read the contents of a file.
        
        Args:
            path: Path to the file to read.
            
        Returns:
            The content of the file, or an error message.
        """
        success, content = file_manager.read_file(path)
        if not success:
            logger.error(f"Failed to read file: {content}")
            return f"Error: {content}"
        return content

    @mcp.tool()
    async def edit_file(path: str, content: str) -> str:
        """Write content to a file.
        
        Args:
            path: Path to the file to write.
            content: Content to write to the file.
            
        Returns:
            A message indicating success or failure.
        """
        success, message = file_manager.write_file(path, content)
        if not success:
            logger.error(f"Failed to write file: {message}")
            return f"Error: {message}"
        return message

    @mcp.tool()
    async def change_in_file(path: str, original: str, modified: str) -> str:
        """Apply changes to a file using diff comparison.
        
        Args:
            path: Path to the file to modify.
            original: Original content.
            modified: Modified content.
            
        Returns:
            A message indicating success or failure.
        """
        success, message = file_manager.apply_diff(path, original, modified)
        if not success:
            logger.error(f"Failed to apply diff: {message}")
            return f"Error: {message}"
        return message

    @mcp.tool()
    async def list_files(path: str, recursive: bool = False) -> Dict[str, Any]:
        """List files and directories within a directory.
        
        Args:
            path: Path to the directory.
            recursive: Whether to list files recursively.
            
        Returns:
            Dictionary containing file listing or error information.
        """
        success, results = file_manager.list_files(path, recursive)
        if not success or isinstance(results, str):
            logger.error(f"Failed to list files: {results}")
            return {
                "success": False,
                "message": f"Error: {results}",
                "files": []
            }
        
        if not results:
            return {
                "success": True,
                "message": "Directory is empty.",
                "files": []
            }
            
        # Convert datetime objects to strings for JSON serialization
        for item in results:
            if item["modified"] is not None:
                from datetime import datetime
                item["modified"] = datetime.fromtimestamp(item["modified"]).isoformat()
        
        # Return structured data
        return {
            "success": True,
            "message": f"Listed {len(results)} items",
            "path": path,
            "recursive": recursive,
            "files": results
        }

    @mcp.tool()
    async def search_files(pattern: str, path: str, file_pattern: Optional[str] = None) -> str:
        """Search for a pattern in files.
        
        Args:
            pattern: Regular expression pattern to search for.
            path: Path to search in.
            file_pattern: Optional glob pattern to filter files.
            
        Returns:
            Search results or an error message.
        """
        success, results = file_manager.search_files(pattern, path, file_pattern)
        if not success or isinstance(results, str):
            logger.error(f"Failed to search files: {results}")
            return f"Error: {results}"
        
        # Format search results
        if not results:
            return "No matches found."
            
        formatted_results = []
        for match in results:
            formatted_results.append(
                f"File: {match['path']}, Line {match['line']}: {match['content']}"
            )
            
        return "\n".join(formatted_results)
