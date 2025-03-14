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
        """Apply a diff to a file by replacing a specific chunk with another.

        Args:
            path: Path to the file.
            original: Original content chunk to replace.
            modified: Modified content chunk to insert.

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

            # Check if original content exists in the file
            if original not in current_content:
                return False, "Original content not found in file"

            # Replace the chunk
            updated_content = current_content.replace(original, modified)
            
            # If no changes were made, return error
            if current_content == updated_content:
                return False, "No changes were made to the file"

            # Write the updated content to the file
            return self.write_file(path, updated_content)
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
    
    def find_files(
        self, 
        path: Union[str, Path],
        pattern: Optional[str] = None,
        respect_gitignore: bool = True,
        file_type: Optional[str] = None,
        max_depth: Optional[int] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
    ) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """Find files in a directory based on various criteria, respecting .gitignore.
        
        Args:
            path: Path to the directory to search in.
            pattern: Optional glob pattern to match filenames.
            respect_gitignore: Whether to respect .gitignore patterns.
            file_type: Optional file type filter ('file', 'dir', or None for both).
            max_depth: Optional maximum recursion depth.
            min_size: Optional minimum file size in bytes.
            max_size: Optional maximum file size in bytes.
            
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
            gitignore_patterns = self._load_gitignore_patterns(path) if respect_gitignore else []
            
            # Traverse directory recursively
            def should_include(item_path: Path, current_depth: int) -> bool:
                """Check if a path should be included in the results based on filters."""
                # Check max depth
                if max_depth is not None and current_depth > max_depth:
                    return False
                    
                # Skip hidden files/dirs unless explicitly included in pattern
                if item_path.name.startswith('.') and (pattern is None or not pattern.startswith('.')):
                    return False
                    
                # Check if path matches gitignore patterns
                if respect_gitignore and self._is_ignored_by_gitignore(item_path, path, gitignore_patterns):
                    return False
                    
                # Check file type filter
                if file_type == 'file' and not item_path.is_file():
                    return False
                if file_type == 'dir' and not item_path.is_dir():
                    return False
                    
                # Check file size constraints for files
                if item_path.is_file():
                    size = item_path.stat().st_size
                    if min_size is not None and size < min_size:
                        return False
                    if max_size is not None and size > max_size:
                        return False
                        
                # Check if file matches pattern
                if pattern is not None:
                    import fnmatch
                    if not fnmatch.fnmatch(item_path.name, pattern):
                        return False
                        
                return True
                
            # Walk directory with custom logic
            def walk_directory(current_path: Path, current_depth: int = 0):
                try:
                    for item in current_path.iterdir():
                        if should_include(item, current_depth):
                            relative_path = item.relative_to(path)
                            item_info = {
                                "name": item.name,
                                "path": str(relative_path),
                                "is_dir": item.is_dir(),
                                "size": item.stat().st_size if item.is_file() else None,
                                "modified": item.stat().st_mtime,
                            }
                            result.append(item_info)
                            
                        # Recursively process directories
                        if item.is_dir() and (max_depth is None or current_depth < max_depth):
                            # Skip directories that match gitignore patterns
                            if not (respect_gitignore and self._is_ignored_by_gitignore(item, path, gitignore_patterns)):
                                walk_directory(item, current_depth + 1)
                except PermissionError:
                    # Skip directories we don't have permission to access
                    pass
                    
            # Start the recursive walk
            walk_directory(path)
            
            # Sort results: directories first, then files, both alphabetically
            result.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            
            return True, result
        except Exception as e:
            error_msg = f"Failed to find files in {path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    def _load_gitignore_patterns(self, path: Path) -> List[str]:
        """Load gitignore patterns from all .gitignore files in the path hierarchy.
        
        Args:
            path: Base path to start looking for .gitignore files
            
        Returns:
            List of gitignore patterns
        """
        patterns = []
        
        # Find all .gitignore files in the path and its parents
        current = path
        while current != current.parent:  # Stop at filesystem root
            gitignore_path = current / '.gitignore'
            if gitignore_path.is_file():
                try:
                    content = gitignore_path.read_text(encoding='utf-8')
                    for line in content.splitlines():
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            patterns.append((current, line))
                except Exception as e:
                    logger.warning(f"Failed to read .gitignore at {gitignore_path}: {str(e)}")
            current = current.parent
            
        return patterns
        
    def _is_ignored_by_gitignore(self, file_path: Path, base_path: Path, patterns: List[Tuple[Path, str]]) -> bool:
        """Check if a file is ignored by any of the gitignore patterns.
        
        Args:
            file_path: Path to the file to check
            base_path: Base path where the search started
            patterns: List of (directory, pattern) tuples from .gitignore files
            
        Returns:
            True if the file should be ignored, False otherwise
        """
        try:
            import fnmatch
            
            # Get the relative path from the base of the repository
            for pattern_dir, pattern in patterns:
                # The pattern should be applied relative to the directory containing the .gitignore file
                try:
                    relative_path = file_path.relative_to(pattern_dir)
                    relative_str = str(relative_path)
                    
                    # Handle negation patterns (patterns starting with !)
                    if pattern.startswith('!'):
                        negated_pattern = pattern[1:]
                        if fnmatch.fnmatch(relative_str, negated_pattern):
                            return False
                    # Handle directory-only patterns (ending with /)
                    elif pattern.endswith('/'):
                        dir_pattern = pattern.rstrip('/')
                        if file_path.is_dir() and fnmatch.fnmatch(relative_str, dir_pattern):
                            return True
                    # Handle standard patterns
                    elif fnmatch.fnmatch(relative_str, pattern):
                        return True
                    # Handle subdirectory patterns (e.g., "dir/" should match "dir/file.txt")
                    elif '/' in pattern:
                        # Split into directory and file parts
                        pattern_dir_part = pattern.split('/')[0]
                        if file_path.is_dir() and file_path.name == pattern_dir_part:
                            return True
                except ValueError:
                    # If file_path is not relative to pattern_dir, skip this pattern
                    continue
                    
            return False
        except Exception as e:
            logger.warning(f"Error checking gitignore patterns: {str(e)}")
            return False
    
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
