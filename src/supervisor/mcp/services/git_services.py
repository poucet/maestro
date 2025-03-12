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
    logger.info("Registering Git operation MCP services")
    
    @mcp.tool()
    async def git_commit(message: str, files: Optional[List[str]] = None) -> str:
        """Commit changes to the Git repository.
        
        Args:
            message: Commit message.
            files: Optional list of files to commit. If None, commits all changes.
            
        Returns:
            A message indicating success or failure.
        """
        files_str = str(files) if files else "all changes"
        logger.info(f"MCP Tool Call: git_commit(message='{message}', files={files_str})")
        
        file_paths = [Path(f) for f in files] if files else None
        success, result = version_control_manager.commit(message, file_paths)
        
        if not success:
            logger.error(f"MCP Tool git_commit FAILED: {result}")
            return f"Error: {result}"
        
        logger.info(f"MCP Tool git_commit SUCCESS: {result}")
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
        logger.info(f"MCP Tool Call: git_restore(files={files}, staged={staged})")
        
        file_paths = [Path(f) for f in files]
        success, message = version_control_manager.restore(file_paths, staged)
        
        if not success:
            logger.error(f"MCP Tool git_restore FAILED: {message}")
            return f"Error: {message}"
        
        logger.info(f"MCP Tool git_restore SUCCESS: {message}")
        return message
    
    @mcp.tool()
    async def git_status() -> Dict[str, Any]:
        """Get the current status of the Git repository.
        
        Returns:
            A dictionary containing the status output or error message.
        """
        logger.info(f"MCP Tool Call: git_status()")
        
        # Get machine-readable status
        success, porcelain_status = version_control_manager.get_status()
        if not success:
            logger.error(f"MCP Tool git_status FAILED: {porcelain_status}")
            return {"success": False, "message": f"Error: {porcelain_status}"}
            
        # Get human-readable status
        success, detailed_status = version_control_manager.get_detailed_status()
        if not success:
            logger.error(f"MCP Tool git_status FAILED: {detailed_status}")
            return {"success": False, "message": f"Error: {detailed_status}"}
        
        # Count changed files
        changed_files = len([line for line in porcelain_status.split("\n") if line])
        logger.info(f"MCP Tool git_status SUCCESS: Repository has {changed_files} changed files")
            
        return {
            "success": True,
            "status": detailed_status,
            "files": [line for line in porcelain_status.split("\n") if line]
        }
    
    @mcp.tool()
    async def git_log(count: int = 10, all_branches: bool = False, 
                     format: str = "oneline") -> Dict[str, Any]:
        """Get the commit history of the Git repository.
        
        Args:
            count: Number of commits to retrieve (default: 10).
            all_branches: If True, shows commits from all branches (default: False).
            format: Format of the log output (default: "oneline").
                Options: "oneline", "short", "medium", "full", "fuller"
            
        Returns:
            A dictionary containing the log output or error message.
        """
        logger.info(f"MCP Tool Call: git_log(count={count}, all_branches={all_branches}, format='{format}')")
        
        success, log_output = version_control_manager.get_log(count, all_branches, format)
        if not success:
            logger.error(f"MCP Tool git_log FAILED: {log_output}")
            return {"success": False, "message": f"Error: {log_output}"}
            
        # Split the log output into lines for easier parsing
        log_entries = [line for line in log_output.split("\n") if line]
        
        logger.info(f"MCP Tool git_log SUCCESS: Retrieved {len(log_entries)} commits")
        return {
            "success": True,
            "count": len(log_entries),
            "format": format,
            "all_branches": all_branches,
            "entries": log_entries
        }
    
    @mcp.tool()
    async def git_show(commit_hash: str = "HEAD") -> Dict[str, Any]:
        """Show details of a specific commit.
        
        Args:
            commit_hash: Hash of the commit to show (default: "HEAD").
            
        Returns:
            A dictionary containing the commit details or error message.
        """
        logger.info(f"MCP Tool Call: git_show(commit_hash='{commit_hash}')")
        
        success, show_output = version_control_manager.get_show(commit_hash)
        if not success:
            logger.error(f"MCP Tool git_show FAILED: {show_output}")
            return {"success": False, "message": f"Error: {show_output}"}
        
        output_preview = show_output[:100] + "..." if len(show_output) > 100 else show_output
        logger.info(f"MCP Tool git_show SUCCESS: Retrieved details for commit '{commit_hash}', preview: {output_preview}")
            
        return {
            "success": True,
            "commit": commit_hash,
            "details": show_output
        }
    
    @mcp.tool()
    async def git_diff(file_path: Optional[str] = None, staged: bool = False) -> Dict[str, Any]:
        """Get the diff of files in the repository.
        
        Args:
            file_path: Optional path to a specific file.
            staged: If True, shows diff for staged changes (default: False).
            
        Returns:
            A dictionary containing the diff output or error message.
        """
        file_info = f"file='{file_path}'" if file_path else "all files"
        logger.info(f"MCP Tool Call: git_diff({file_info}, staged={staged})")
        
        success, diff_output = version_control_manager.get_diff(
            Path(file_path) if file_path else None, 
            staged
        )
        if not success:
            logger.error(f"MCP Tool git_diff FAILED: {diff_output}")
            return {"success": False, "message": f"Error: {diff_output}"}
        
        # Count lines of diff for logging
        diff_lines = len(diff_output.split("\n"))
        logger.info(f"MCP Tool git_diff SUCCESS: Retrieved {diff_lines} lines of diff for {file_info}, staged={staged}")
            
        return {
            "success": True,
            "staged": staged,
            "file": file_path,
            "diff": diff_output
        }
    
    @mcp.tool()
    async def git_branch(all_branches: bool = False) -> Dict[str, Any]:
        """Get the list of branches in the repository.
        
        Args:
            all_branches: If True, shows remote branches as well (default: False).
            
        Returns:
            A dictionary containing the branch list or error message.
        """
        logger.info(f"MCP Tool Call: git_branch(all_branches={all_branches})")
        
        success, branch_output = version_control_manager.get_branch_list(all_branches)
        if not success:
            logger.error(f"MCP Tool git_branch FAILED: {branch_output}")
            return {"success": False, "message": f"Error: {branch_output}"}
            
        # Parse branch output
        branches = [line.strip() for line in branch_output.split("\n") if line.strip()]
        current_branch = None
        
        # Find the current branch (marked with *)
        for i, branch in enumerate(branches):
            if branch.startswith("*"):
                current_branch = branch[1:].strip()
                branches[i] = branch[1:].strip()
        
        logger.info(f"MCP Tool git_branch SUCCESS: Found {len(branches)} branches, current branch: {current_branch}")
                
        return {
            "success": True,
            "all_branches": all_branches,
            "current_branch": current_branch,
            "branches": branches
        }
