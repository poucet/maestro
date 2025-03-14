"""MCP services for file operations."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from mcp.server.fastmcp import FastMCP

from simply_maestro.core import FileManager

logger = logging.getLogger(__name__)


def register_file_services(mcp: FastMCP, file_manager: FileManager) -> None:
    """Register file operation MCP services.

    Args:
        mcp: MCP server instance.
        file_manager: File manager instance.
    """
    logger.info("Registering file management MCP services")
    
    @mcp.tool()
    async def read_file(path: str) -> str:
        """Read the contents of a file.
        
        Args:
            path: Path to the file to read.
            
        Returns:
            The content of the file, or an error message.
        """
        logger.info(f"MCP Tool Call: read_file(path='{path}')")
        success, content = file_manager.read_file(path)
        if not success:
            logger.error(f"MCP Tool read_file FAILED: {content}")
            return f"Error: {content}"
        
        content_preview = content[:100] + "..." if len(content) > 100 else content
        logger.info(f"MCP Tool read_file SUCCESS: Read {len(content)} bytes from '{path}', preview: {content_preview}")
        return content

    @mcp.tool()
    async def write_file(path: str, content: str) -> str:
        """Write content to a file.
        
        Args:
            path: Path to the file to write.
            content: Content to write to the file.
            
        Returns:
            A message indicating success or failure.
        """
        content_preview = content[:100] + "..." if len(content) > 100 else content
        logger.info(f"MCP Tool Call: edit_file(path='{path}', content='{content_preview}')")
        
        success, message = file_manager.write_file(path, content)
        if not success:
            logger.error(f"MCP Tool edit_file FAILED: {message}")
            return f"Error: {message}"
        
        logger.info(f"MCP Tool edit_file SUCCESS: {message}")
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
        original_preview = original[:50] + "..." if len(original) > 50 else original
        modified_preview = modified[:50] + "..." if len(modified) > 50 else modified
        logger.info(f"MCP Tool Call: change_in_file(path='{path}', original='{original_preview}', modified='{modified_preview}')")
        
        success, message = file_manager.apply_diff(path, original, modified)
        if not success:
            logger.error(f"MCP Tool change_in_file FAILED: {message}")
            return f"Error: {message}"
        
        logger.info(f"MCP Tool change_in_file SUCCESS: {message}")
        return message

    @mcp.tool()
    async def list_files(path: str = ".", recursive: bool = False) -> Dict[str, Any]:
        """List files and directories within a directory.
        
        Args:
            path: Path to the directory. Defaults to current directory.
            recursive: Whether to list files recursively.
            
        Returns:
            Dictionary containing file listing or error information.
        """
        # Set default path if not provided
        if not path:
            path = "."
            
        logger.info(f"MCP Tool Call: list_files(path='{path}', recursive={recursive})")
        
        success, results = file_manager.list_files(path, recursive)
        if not success or isinstance(results, str):
            logger.error(f"MCP Tool list_files FAILED: {results}")
            return {
                "success": False,
                "message": f"Error: {results}",
                "files": []
            }
        
        if not results:
            logger.info(f"MCP Tool list_files SUCCESS: Directory '{path}' is empty")
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
        logger.info(f"MCP Tool list_files SUCCESS: Listed {len(results)} items in '{path}'")
        return {
            "success": True,
            "message": f"Listed {len(results)} items",
            "path": path,
            "recursive": recursive,
            "files": results
        }

    @mcp.tool()
    async def find_files(
        path: str, 
        pattern: Optional[str] = None,
        respect_gitignore: bool = True,
        file_type: Optional[str] = None,
        max_depth: Optional[int] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Find files in a directory based on various criteria, respecting .gitignore.
        
        Args:
            path: Path to the directory to search in.
            pattern: Optional glob pattern to match filenames (e.g., "*.py").
            respect_gitignore: Whether to respect .gitignore patterns (default: True).
            file_type: Optional file type filter ('file', 'dir', or None for both).
            max_depth: Optional maximum directory depth to search.
            min_size: Optional minimum file size in bytes.
            max_size: Optional maximum file size in bytes.
            
        Returns:
            Dictionary containing search results or error information.
        """
        # Log tool call with all parameters for diagnostic purposes
        logger.info(
            f"MCP Tool Call: find_files(path='{path}', pattern={pattern}, "
            f"respect_gitignore={respect_gitignore}, file_type={file_type}, "
            f"max_depth={max_depth}, min_size={min_size}, max_size={max_size})"
        )
        
        # Call the core file manager method
        success, results = file_manager.find_files(
            path=path,
            pattern=pattern,
            respect_gitignore=respect_gitignore,
            file_type=file_type,
            max_depth=max_depth,
            min_size=min_size,
            max_size=max_size
        )
        
        if not success or isinstance(results, str):
            logger.error(f"MCP Tool find_files FAILED: {results}")
            return {
                "success": False,
                "message": f"Error: {results}",
                "files": []
            }
        
        if not results:
            logger.info(f"MCP Tool find_files SUCCESS: No files found matching criteria in '{path}'")
            return {
                "success": True,
                "message": "No files found matching the specified criteria.",
                "files": []
            }
            
        # Convert datetime objects to strings for JSON serialization
        for item in results:
            if item["modified"] is not None:
                from datetime import datetime
                item["modified"] = datetime.fromtimestamp(item["modified"]).isoformat()
        
        # Return structured data
        result_summary = (
            f"Found {len(results)} items in '{path}'" +
            (f' matching pattern "{pattern}"' if pattern else '') +
            f"{' (respecting .gitignore)' if respect_gitignore else ''}"
        )
        
        logger.info(f"MCP Tool find_files SUCCESS: {result_summary}")
        return {
            "success": True,
            "message": result_summary,
            "path": path,
            "pattern": pattern,
            "respect_gitignore": respect_gitignore,
            "file_type": file_type,
            "count": len(results),
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
        file_pattern_info = f", file_pattern='{file_pattern}'" if file_pattern else ""
        logger.info(f"MCP Tool Call: search_files(pattern='{pattern}', path='{path}'{file_pattern_info})")
        
        success, results = file_manager.search_files(pattern, path, file_pattern)
        if not success or isinstance(results, str):
            logger.error(f"MCP Tool search_files FAILED: {results}")
            return f"Error: {results}"
        
        # Format search results
        if not results:
            logger.info(f"MCP Tool search_files SUCCESS: No matches found for pattern '{pattern}' in '{path}'")
            return "No matches found."
            
        formatted_results = []
        for match in results:
            formatted_results.append(
                f"File: {match['path']}, Line {match['line']}: {match['content']}"
            )
        
        logger.info(f"MCP Tool search_files SUCCESS: Found {len(results)} matches for pattern '{pattern}' in '{path}'")
        return "\n".join(formatted_results)
