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
    port: Optional[int] = None  # Port that the process listens on, if applicable
    log_to_file: bool = True  # Whether to log process output to a file
    log_file_path: Optional[Path] = None  # Path to the log file, or None to use default


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
        self._log_file_handle = None
        
        # Set up log file if configured
        if self.config.log_to_file:
            self._setup_log_file()
            
    def _setup_log_file(self) -> None:
        """Set up the log file for process output."""
        if not self.config.log_to_file:
            return
            
        # Determine log file path
        log_path = self.config.log_file_path
        if log_path is None:
            # Use default path in logs directory
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Create a log filename based on the command
            if isinstance(self.config.command, list):
                cmd_name = self.config.command[0].split("/")[-1]
            else:
                cmd_name = self.config.command.split()[0].split("/")[-1]
                
            # Add timestamp to log filename
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = log_dir / f"{cmd_name}_{timestamp}.log"
            
        logger.info(f"Process output will be logged to: {log_path}")
        self._log_file_path = log_path

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

    def _find_process_by_port(self) -> Optional[int]:
        """Find a process that is listening on the configured port.
        
        Returns:
            Process ID if found, None otherwise.
        """
        if self.config.port is None:
            return None
            
        try:
            # Use psutil to find all network connections
            for conn in psutil.net_connections(kind='inet'):
                # Check if this connection is listening on our port
                if conn.status == 'LISTEN' and conn.laddr.port == self.config.port:
                    return conn.pid
        except (psutil.AccessDenied, psutil.Error) as e:
            logger.warning(f"Error checking for processes listening on port {self.config.port}: {str(e)}")
        
        return None
    
    def attach_to_existing_process(self) -> Tuple[bool, str]:
        """Try to attach to an existing process running on the configured port.
        
        Returns:
            Tuple of (success, message).
        """
        if self.config.port is None:
            return False, "No port configured to find existing process"
            
        if self.is_running:
            return True, "Already attached to a running process"
            
        pid = self._find_process_by_port()
        if pid is None:
            return False, f"No process found listening on port {self.config.port}"
            
        try:
            # Attach to the existing process
            self._pid = pid
            # We don't have a subprocess.Popen object for an existing process
            self._process = None  
            
            logger.info(f"Attached to existing process: PID={self._pid}")
            return True, f"Attached to existing process with PID: {self._pid}"
        except Exception as e:
            error_msg = f"Failed to attach to existing process: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def start(self) -> Tuple[bool, str]:
        """Start the managed process or attach to an existing one.

        Returns:
            Tuple of (success, message).
        """
        if self.is_running:
            return True, "Process is already running"
            
        # First try to attach to an existing process if a port is configured
        if self.config.port is not None:
            success, message = self.attach_to_existing_process()
            if success:
                return success, message
            logger.info(f"No existing process found on port {self.config.port}, starting new process")
            
        self._restart_count = 0
        try:
            cmd = self.config.command
            if isinstance(cmd, str):
                cmd = cmd.split()

            env = os.environ.copy()
            if self.config.env:
                env.update(self.config.env)

            # Setup stdout/stderr handling for proper Unix file descriptor passing
            stdout_dest = None
            stderr_dest = None
            log_file_handle = None
            
            # Handle log file setup
            if self.config.log_to_file and hasattr(self, '_log_file_path'):
                # Create parent directories if needed
                self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Open log file directly - this will be passed to the subprocess
                # so it will continue logging even if supervisor dies
                log_file_handle = open(self._log_file_path, 'w', encoding='utf-8')
                self._log_file_handle = log_file_handle
                logger.info(f"Opened log file for direct process output: {self._log_file_path}")
                
                if self.config.capture_output:
                    # Need to set up a tee-like mechanism for output capture while still logging
                    # For simplicity, let's just set up a pipe and forward output to the file
                    stdout_dest = subprocess.PIPE
                    stderr_dest = subprocess.STDOUT
                else:
                    # Process writes directly to log file, supervisor doesn't capture
                    stdout_dest = log_file_handle
                    stderr_dest = subprocess.STDOUT
            else:
                # No log file, just capture output if configured
                stdout_dest = subprocess.PIPE if self.config.capture_output else None
                stderr_dest = subprocess.STDOUT if self.config.capture_output else None

            # Use start_new_session=True to decouple the child process from the supervisor
            # This ensures the child process will continue running even if the supervisor dies
            self._process = subprocess.Popen(
                cmd,
                cwd=self.config.working_dir,
                env=env,
                stdout=stdout_dest,
                stderr=stderr_dest,
                text=True,
                bufsize=1,
                universal_newlines=True,
                start_new_session=True,  # Create a new process group
            )
            self._pid = self._process.pid

            logger.info(f"Started process: PID={self._pid}")

            if self.config.capture_output and self._process.stdout:
                # Run in background without blocking the start method
                asyncio.ensure_future(self._read_output())

            return True, f"Process started with PID: {self._pid}"
        except Exception as e:
            # Clean up any open file handles on error
            if hasattr(self, '_log_file_handle') and self._log_file_handle and not self._log_file_handle.closed:
                self._log_file_handle.close()
                self._log_file_handle = None
                
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
            
            # Clean up our file handle if we still have it open
            # Note: We don't close the file handle that's passed to the subprocess as
            # that would be closed automatically when the subprocess exits
            if hasattr(self, '_log_file_handle') and self._log_file_handle and not self._log_file_handle.closed:
                try:
                    self._log_file_handle.close()
                    logger.info(f"Closed log file handle on process stop")
                except Exception as e:
                    logger.error(f"Error closing log file handle: {str(e)}")
                self._log_file_handle = None
            
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

        # Run the blocking readline() calls in a separate thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        
        def read_output_thread():
            if self._process is None or self._process.stdout is None:
                return
                
            try:
                for line in iter(self._process.stdout.readline, ''):
                    if not line:
                        break
                        
                    line = line.rstrip()
                    logger.debug(f"Process output: {line}")
                    
                    # If we're using capture_output and log_to_file together,
                    # we need to manually write to the log file
                    if self.config.capture_output and self.config.log_to_file and \
                       hasattr(self, '_log_file_handle') and self._log_file_handle and not self._log_file_handle.closed:
                        try:
                            self._log_file_handle.write(f"{line}\n")
                            self._log_file_handle.flush()  # Ensure it's written immediately
                        except Exception as e:
                            logger.error(f"Error writing to log file: {str(e)}")
                    
                    if self._output_callback:
                        self._output_callback(line)
            except Exception as e:
                logger.error(f"Error reading process output: {str(e)}")
        
        # Run in a thread pool to avoid blocking the event loop
        await loop.run_in_executor(None, read_output_thread)

        # Check if process has exited
        if self._process and self._process.poll() is not None:
            exit_code = self._process.returncode
            logger.info(f"Process exited with code: {exit_code}")
            
            # Clean up our file handle if we still have it open
            if hasattr(self, '_log_file_handle') and self._log_file_handle and not self._log_file_handle.closed:
                try:
                    self._log_file_handle.close()
                    logger.info(f"Closed log file handle on process exit")
                except Exception as e:
                    logger.error(f"Error closing log file handle: {str(e)}")
                self._log_file_handle = None
            
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
