"""MCP services for process management."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from mcp.server import FastMCP

from simply_maestro.core import ProcessManager

logger = logging.getLogger(__name__)


def register_process_services(mcp: FastMCP, process_manager: ProcessManager) -> None:
    """Register process management MCP services.

    Args:
        mcp: MCP server instance.
        process_manager: Process manager instance.
    """
    logger.info("Registering process management MCP services")
    
    # Path to logs directory
    logs_dir = Path("logs")
    
    @mcp.tool()
    async def stop_task() -> str:
        """Stop the managed process.
        
        Note: Since the target process has its own babysitter, Simply Maestro
        only needs to stop processes when explicitly requested.
        
        Returns:
            A message indicating success or failure.
        """
        logger.info(f"MCP Tool Call: stop_task()")
        
        stop_success, stop_message = await process_manager.stop()
        if not stop_success:
            logger.error(f"MCP Tool stop_task FAILED: {stop_message}")
            return f"Error stopping process: {stop_message}"
        
        logger.info(f"MCP Tool stop_task SUCCESS: {stop_message}")
        return stop_message

    @mcp.tool()
    async def start_task() -> str:
        """Monitor an existing managed process or start if needed.
        
        Note: This tool primarily attaches to an existing process for monitoring.
        The target process is expected to have its own babysitter for restart.
        
        Returns:
            A message indicating success or failure.
        """
        logger.info(f"MCP Tool Call: start_task()")
        
        success, message = await process_manager.start()
        if not success:
            logger.error(f"MCP Tool start_task FAILED: {message}")
            return f"Error: {message}"
        
        logger.info(f"MCP Tool start_task SUCCESS: {message}")
        return message

    @mcp.tool()
    async def restart_task() -> str:
        """Emergency restart of the managed process.
        
        Note: This should only be used in emergency situations as the target
        process is expected to have its own babysitter for normal restart operations.
        
        Returns:
            A message indicating success or failure.
        """
        logger.info(f"MCP Tool Call: restart_task() - EMERGENCY USE ONLY")
        
        # First ensure the process is fully stopped
        logger.info(f"MCP Tool restart_task - Phase 1: Stopping process")
        stop_success, stop_message = await process_manager.stop()
        if not stop_success:
            logger.error(f"MCP Tool restart_task FAILED during stop phase: {stop_message}")
            return f"Error stopping process: {stop_message}"
            
        # Give it a moment to fully shut down
        await asyncio.sleep(1.0)
        
        # Now start a fresh process, forcing a new process (don't try to attach to existing)
        logger.info(f"MCP Tool restart_task - Phase 2: Starting new process")
        start_success, start_message = await process_manager.start(force_new_process=True)
        if not start_success:
            logger.error(f"MCP Tool restart_task FAILED during start phase: {start_message}")
            return f"Error starting process: {start_message}"
            
        logger.info(f"MCP Tool restart_task SUCCESS: Process restarted with PID {process_manager._pid}")
        return f"Process restarted successfully: {start_message}"
    
    @mcp.tool()
    async def list_process_logs() -> Dict[str, Any]:
        """List available process log files.
        
        Returns:
            A dictionary containing log file information.
        """
        logger.info(f"MCP Tool Call: list_process_logs()")
        
        try:
            if not logs_dir.exists():
                logger.warning(f"MCP Tool list_process_logs: Logs directory not found at {logs_dir}")
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
                
            logger.info(f"MCP Tool list_process_logs SUCCESS: Found {len(log_files)} log files")
            return {
                "success": True,
                "message": f"Found {len(log_files)} log files",
                "logs": log_files
            }
        except Exception as e:
            error_msg = f"Failed to list log files: {str(e)}"
            logger.error(f"MCP Tool list_process_logs FAILED: {error_msg}")
            return {"success": False, "message": error_msg, "logs": []}

    @mcp.tool()
    async def read_process_log(filename: str) -> Dict[str, Any]:
        """Read the contents of a specific process log file.
        
        Args:
            filename: Name of the log file to read.
            
        Returns:
            A dictionary containing the log file content or error message.
        """
        logger.info(f"MCP Tool Call: read_process_log(filename='{filename}')")
        
        try:
            log_path = logs_dir / filename
            
            # Security check - ensure the file is within the logs directory
            if not log_path.is_relative_to(logs_dir):
                logger.warning(f"MCP Tool read_process_log security check FAILED: Path traversal attempt with '{filename}'")
                return {
                    "success": False, 
                    "message": "Invalid log file path"
                }
                
            if not log_path.exists() or not log_path.is_file():
                logger.warning(f"MCP Tool read_process_log FAILED: Log file not found: {filename}")
                return {
                    "success": False, 
                    "message": f"Log file not found: {filename}"
                }
                
            content = log_path.read_text(encoding="utf-8")
            content_size = len(content)
            
            logger.info(f"MCP Tool read_process_log SUCCESS: Read {content_size} bytes from log file '{filename}'")
            return {
                "success": True,
                "message": f"Read log file: {filename}",
                "filename": filename,
                "content": content,
                "size": log_path.stat().st_size
            }
        except Exception as e:
            error_msg = f"Failed to read log file {filename}: {str(e)}"
            logger.error(f"MCP Tool read_process_log FAILED: {error_msg}")
            return {"success": False, "message": error_msg}
