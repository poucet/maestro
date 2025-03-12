"""Process management functionality for the supervisor."""

import asyncio
import logging
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ProcessConfig:
    """Configuration for a managed process."""

    command: Union[str, List[str]]
    working_dir: Path
    env: Optional[Dict[str, str]] = None
    restart_delay: float = 1.0
    max_restart_attempts: int = 3
    capture_output: bool = True


class ProcessManager:
    """Manages the lifecycle of a target process."""

    def __init__(self, config: ProcessConfig) -> None:
        """Initialize the process manager.

        Args:
            config: Configuration for the managed process.
        """
        self.config = config
        self._process: Optional[subprocess.Popen] = None
        self._pid: Optional[int] = None
        self._restart_count = 0
        self._output_callback: Optional[Callable[[str], None]] = None

    @property
    def is_running(self) -> bool:
        """Check if the managed process is currently running.

        Returns:
            True if the process is running, False otherwise.
        """
        if self._process is None or self._pid is None:
            return False

        try:
            process = psutil.Process(self._pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

    async def start(self) -> Tuple[bool, str]:
        """Start the managed process.

        Returns:
            Tuple of (success, message).
        """
        if self.is_running:
            return True, "Process is already running"

        self._restart_count = 0
        try:
            cmd = self.config.command
            if isinstance(cmd, str):
                cmd = cmd.split()

            env = os.environ.copy()
            if self.config.env:
                env.update(self.config.env)

            # Use start_new_session=True to decouple the child process from the supervisor
            # This ensures the child process will continue running even if the supervisor dies
            self._process = subprocess.Popen(
                cmd,
                cwd=self.config.working_dir,
                env=env,
                stdout=subprocess.PIPE if self.config.capture_output else None,
                stderr=subprocess.STDOUT if self.config.capture_output else None,
                text=True,
                bufsize=1,
                universal_newlines=True,
                start_new_session=True,  # Create a new process group
                preexec_fn=os.setpgrp if os.name == 'posix' else None,  # Only on Unix-like systems
            )
            self._pid = self._process.pid

            logger.info(f"Started process: PID={self._pid}")

            if self.config.capture_output and self._process.stdout:
                # Run in background without blocking the start method
                asyncio.ensure_future(self._read_output())

            return True, f"Process started with PID: {self._pid}"
        except Exception as e:
            error_msg = f"Failed to start process: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def stop(self) -> Tuple[bool, str]:
        """Stop the managed process.

        Returns:
            Tuple of (success, message).
        """
        if not self.is_running:
            return True, "Process is not running"

        if self._pid is None:
            return False, "No process ID available"

        try:
            process = psutil.Process(self._pid)
            
            # Terminate process group if on Unix-like system
            if os.name == 'posix':
                try:
                    # Get all child processes before terminating the parent
                    children = process.children(recursive=True)
                    
                    # First try to terminate the process group gracefully
                    os.killpg(os.getpgid(self._pid), signal.SIGTERM)
                    
                    # Wait for the main process to terminate
                    try:
                        process.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        # Force kill the process group if timeout
                        os.killpg(os.getpgid(self._pid), signal.SIGKILL)
                    
                    # Ensure all children are terminated
                    for child in children:
                        try:
                            if child.is_running():
                                child.kill()
                        except psutil.NoSuchProcess:
                            pass
                except (ProcessLookupError, PermissionError) as e:
                    logger.warning(f"Error terminating process group: {str(e)}")
                    # Fall back to regular process termination
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        process.kill()
            else:
                # On Windows, just terminate the process normally
                process.terminate()
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    process.kill()
            
            self._process = None
            self._pid = None
            
            return True, "Process stopped"
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            error_msg = f"Failed to stop process: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def restart(self) -> Tuple[bool, str]:
        """Restart the managed process.

        Returns:
            Tuple of (success, message).
        """
        await self.stop()
        await asyncio.sleep(self.config.restart_delay)
        return await self.start()

    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """Set a callback to receive process output.

        Args:
            callback: Function to call with each line of output.
        """
        self._output_callback = callback

    async def _read_output(self) -> None:
        """Read and process output from the managed process."""
        if self._process is None or self._process.stdout is None:
            return

        while True:
            line = self._process.stdout.readline()
            if not line:
                break

            line = line.rstrip()
            logger.debug(f"Process output: {line}")

            if self._output_callback:
                self._output_callback(line)

        # Check if process has exited
        if self._process.poll() is not None:
            exit_code = self._process.returncode
            logger.info(f"Process exited with code: {exit_code}")
            self._process = None
            self._pid = None

            # Auto-restart if needed
            if self._restart_count < self.config.max_restart_attempts:
                self._restart_count += 1
                logger.info(
                    f"Auto-restarting process (attempt {self._restart_count})"
                )
                await asyncio.sleep(self.config.restart_delay)
                await self.start()
