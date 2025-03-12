"""Version control functionality for the supervisor."""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class VersionControlManager:
    """Manages Git operations for the supervisor."""

    def __init__(self, repo_path: Path) -> None:
        """Initialize the version control manager.

        Args:
            repo_path: Path to the Git repository.
        """
        self.repo_path = repo_path.resolve()

    def _run_git_command(self, args: List[str]) -> Tuple[bool, str]:
        """Run a Git command.

        Args:
            args: Command arguments to pass to Git.

        Returns:
            Tuple of (success, output or error message).
        """
        cmd = ["git"]
        cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                error_msg = f"Git command failed: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg

            return True, result.stdout.strip()
        except Exception as e:
            error_msg = f"Failed to run Git command: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def is_git_repo(self) -> bool:
        """Check if the path is a Git repository.

        Returns:
            True if the path is a Git repository, False otherwise.
        """
        success, _ = self._run_git_command(["rev-parse", "--is-inside-work-tree"])
        return success

    def commit(
        self, message: str, files: Optional[List[Union[str, Path]]] = None
    ) -> Tuple[bool, str]:
        """Commit changes to the repository.

        Args:
            message: Commit message.
            files: Optional list of files to commit. If None, commits all changes.

        Returns:
            Tuple of (success, message).
        """
        if not self.is_git_repo():
            return False, f"Not a Git repository: {self.repo_path}"

        try:
            # Add files to staging area
            if files:
                file_paths = [str(f) for f in files]
                success, result = self._run_git_command(["add", "--"] + file_paths)
            else:
                success, result = self._run_git_command(["add", "--all"])

            if not success:
                return False, f"Failed to stage files: {result}"

            # Commit changes
            success, result = self._run_git_command(["commit", "-m", message])
            if not success:
                # If there's nothing to commit, that's still considered a success
                if "nothing to commit" in result:
                    return True, "Nothing to commit"
                return False, f"Failed to commit: {result}"

            return True, result
        except Exception as e:
            error_msg = f"Failed to commit: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def restore(
        self, files: List[Union[str, Path]], staged: bool = False
    ) -> Tuple[bool, str]:
        """Restore files to their state in the last commit.

        Args:
            files: List of files to restore.
            staged: If True, restore files from the staging area.

        Returns:
            Tuple of (success, message).
        """
        if not self.is_git_repo():
            return False, f"Not a Git repository: {self.repo_path}"

        try:
            file_paths = [str(f) for f in files]
            cmd = ["restore"]
            
            if staged:
                cmd.append("--staged")
                
            cmd.extend(["--"] + file_paths)
            
            success, result = self._run_git_command(cmd)
            if not success:
                return False, f"Failed to restore files: {result}"

            return True, "Files restored successfully"
        except Exception as e:
            error_msg = f"Failed to restore files: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_status(self) -> Tuple[bool, str]:
        """Get the status of the repository.

        Returns:
            Tuple of (success, status).
        """
        if not self.is_git_repo():
            return False, f"Not a Git repository: {self.repo_path}"

        return self._run_git_command(["status", "--porcelain"])
