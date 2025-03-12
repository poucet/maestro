"""MCP services for process management."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from supervisor.core import ProcessManager

logger = logging.getLogger(__name__)


def register_process_services(mcp: FastMCP, process_manager: ProcessManager) -> None:
    """Register process management MCP services.

    Args:
        mcp: MCP server instance.
        process_manager: Process manager instance.
    """
    # Path to logs directory
    logs_dir = Path("logs")
    
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
        # First ensure the process is fully stopped
        logger.info(f"Restarting task: sending stop command...")
        stop_success, stop_message = await process_manager.stop()
        if not stop_success:
            logger.error(f"Failed to stop process: {stop_message}")
            return f"Error stopping process: {stop_message}"
            
        # Give it a moment to fully shut down
        await asyncio.sleep(1.0)
        
        # Force the process manager to set up a new log file for this restart
        if process_manager.config.log_to_file:
            # Re-trigger log file setup to create a new log with a fresh timestamp
            process_manager._setup_log_file()
            logger.info(f"Created new log file for restarted process: {process_manager._log_file_path}")
        
        # Now start a fresh process, forcing a new process (don't try to attach to existing)
        logger.info(f"Starting process after clean shutdown...")
        start_success, start_message = await process_manager.start(force_new_process=True)
        if not start_success:
            logger.error(f"Failed to start process: {start_message}")
            return f"Error starting process: {start_message}"
            
        logger.info(f"Process restarted successfully")
        return f"Process restarted successfully: {start_message}"
    
    @mcp.tool()
    async def list_process_logs() -> Dict[str, Any]:
        """List available process log files.
        
        Returns:
            A dictionary containing log file information.
        """
        try:
            if not logs_dir.exists():
                return {"success": False, "message": "Logs directory not found", "logs": []}
                
            log_files = []
            for log_file in logs_dir.glob("*.log"):
                # Get file stats
                stat = log_file.stat()
                log_files.append({
                    "filename": log_file.name,
                    "path": str(log_file),
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime
                })
                
            # Sort by modified time, newest first
            log_files.sort(key=lambda x: x["modified"], reverse=True)
                
            return {
                "success": True,
                "message": f"Found {len(log_files)} log files",
                "logs": log_files
            }
        except Exception as e:
            error_msg = f"Failed to list log files: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg, "logs": []}

    @mcp.tool()
    async def read_process_log(filename: str) -> Dict[str, Any]:
        """Read the contents of a specific process log file.
        
        Args:
            filename: Name of the log file to read.
            
        Returns:
            A dictionary containing the log file content or error message.
        """
        try:
            log_path = logs_dir / filename
            
            # Security check - ensure the file is within the logs directory
            if not log_path.is_relative_to(logs_dir):
                return {
                    "success": False, 
                    "message": "Invalid log file path"
                }
                
            if not log_path.exists() or not log_path.is_file():
                return {
                    "success": False, 
                    "message": f"Log file not found: {filename}"
                }
                
            content = log_path.read_text(encoding="utf-8")
            return {
                "success": True,
                "message": f"Read log file: {filename}",
                "filename": filename,
                "content": content,
                "size": log_path.stat().st_size
            }
        except Exception as e:
            error_msg = f"Failed to read log file {filename}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
