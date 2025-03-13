"""File management functionality for Simply Maestro."""

import difflib
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

logger = logging.getLogger(__name__)


class FileManager:
    """Manages file operations for Simply Maestro."""

    def __init__(self, allowed_paths: List[Path]) -> None:
        """Initialize the file manager.

        Args:
            allowed_paths: List of paths that can be accessed by the file manager.
        """
        self.allowed_paths = [p.resolve() for p in allowed_paths]

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if a path is within the allowed paths.

        Args:
            path: Path to check.

        Returns:
            True if the path is within the allowed paths, False otherwise.
        """
        path = path.resolve()
        return any(
            path == allowed_path or path.is_relative_to(allowed_path)
            for allowed_path in self.allowed_paths
        )

    def read_file(self, path: Union[str, Path]) -> Tuple[bool, str]:
        """Read the contents of a file.

        Args:
            path: Path to the file.

        Returns:
            Tuple of (success, content or error message).
        """
        path = Path(path).resolve()
        if not self._is_path_allowed(path):
            error_msg = f"Path not allowed: {path}"
            logger.error(error_msg)
            return False, error_msg

        try:
            if not path.exists():
                return False, f"File not found: {path}"

            if not path.is_file():
                return False, f"Not a file: {path}"

            content = path.read_text(encoding="utf-8")
            return True, content
        except Exception as e:
            error_msg = f"Failed to read file {path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def write_file(self, path: Union[str, Path], content: str) -> Tuple[bool, str]:
        """Write content to a file.

        Args:
            path: Path to the file.
            content: Content to write.

        Returns:
            Tuple of (success, message).
        """
        path = Path(path).resolve()
        if not self._is_path_allowed(path):
            error_msg = f"Path not allowed: {path}"
            logger.error(error_msg)
            return False, error_msg

        try:
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup if file exists
            if path.exists():
                backup_path = path.with_suffix(f"{path.suffix}.bak")
                shutil.copy2(path, backup_path)
                logger.info(f"Created backup: {backup_path}")

            # Write content
            path.write_text(content, encoding="utf-8")
            return True, f"File written successfully: {path}"
        except Exception as e:
            error_msg = f"Failed to write file {path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def apply_diff(
        self, path: Union[str, Path], original: str, modified: str
    ) -> Tuple[bool, str]:
        """Apply a diff to a file.

        Args:
            path: Path to the file.
            original: Original content.
            modified: Modified content.

        Returns:
            Tuple of (success, message).
        """
        path = Path(path).resolve()
        if not self._is_path_allowed(path):
            error_msg = f"Path not allowed: {path}"
            logger.error(error_msg)
            return False, error_msg

        try:
            # Read current content
            if not path.exists():
                return False, f"File not found: {path}"

            current_content = path.read_text(encoding="utf-8")

            # Generate unified diff
            diff = difflib.unified_diff(
                current_content.splitlines(),
                modified.splitlines(),
                lineterm="",
            )

            # Apply changes
            return self.write_file(path, modified)
        except Exception as e:
            error_msg = f"Failed to apply diff to {path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def list_files(
        self, path: Union[str, Path], recursive: bool = False
    ) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """List files and directories within a directory.
        
        Args:
            path: Path to the directory.
            recursive: Whether to list files recursively.
            
        Returns:
            Tuple of (success, file list or error message).
        """
        path = Path(path).resolve()
        if not self._is_path_allowed(path):
            error_msg = f"Path not allowed: {path}"
            logger.error(error_msg)
            return False, error_msg
            
        try:
            if not path.exists():
                return False, f"Path not found: {path}"
                
            if not path.is_dir():
                return False, f"Not a directory: {path}"
                
            result = []
            
            if recursive:
                # Handle recursive listing
                for item in path.glob('**/*'):
                    # Skip .git directories and similar hidden files
                    if any(part.startswith('.') for part in item.parts):
                        continue
                        
                    relative_path = item.relative_to(path)
                    
                    item_info = {
                        "name": item.name,
                        "path": str(relative_path),
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else None,
                        "modified": item.stat().st_mtime,
                    }
                    result.append(item_info)
            else:
                # Handle non-recursive listing (top-level only)
                for item in path.iterdir():
                    # Skip hidden files and directories
                    if item.name.startswith('.'):
                        continue
                        
                    item_info = {
                        "name": item.name,
                        "path": item.name,
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else None,
                        "modified": item.stat().st_mtime,
                    }
                    result.append(item_info)
            
            # Sort results: directories first, then files, both alphabetically
            result.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            
            return True, result
        except Exception as e:
            error_msg = f"Failed to list files in {path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def search_files(
        self, pattern: str, path: Union[str, Path], file_pattern: Optional[str] = None
    ) -> Tuple[bool, Union[List[Dict[str, str]], str]]:
        """Search for a pattern in files.

        Args:
            pattern: Regular expression pattern to search for.
            path: Path to search in.
            file_pattern: Optional glob pattern to filter files.

        Returns:
            Tuple of (success, matches or error message).
        """
        path = Path(path).resolve()
        if not self._is_path_allowed(path):
            error_msg = f"Path not allowed: {path}"
            logger.error(error_msg)
            return False, error_msg

        try:
            if not path.exists():
                return False, f"Path not found: {path}"

            # Prepare ripgrep command
            cmd = ["rg", "--json", pattern]
            
            if file_pattern:
                cmd.extend(["--glob", file_pattern])
            
            cmd.append(str(path))

            # Execute ripgrep
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False
            )

            if result.returncode not in [0, 1]:  # 0 = matches found, 1 = no matches
                return False, f"Search failed: {result.stderr}"

            # Parse JSON output
            matches = []
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                    
                try:
                    data = json.loads(line)
                    if data.get("type") == "match":
                        match_data = data.get("data", {})
                        path = match_data.get("path", {}).get("text", "")
                        line_number = match_data.get("line_number", 0)
                        lines = match_data.get("lines", {}).get("text", "")
                        matches.append({
                            "path": path,
                            "line": line_number,
                            "content": lines
                        })
                except json.JSONDecodeError:
                    continue

            return True, matches
        except Exception as e:
            error_msg = f"Failed to search files: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
