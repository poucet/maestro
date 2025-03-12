"""Process management functionality for the supervisor."""

import asyncio
import logging
import os
import signal
import subprocess
import time
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
        
        # Ensure the log directory exists
        self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured log directory exists: {self._log_file_path.parent}")

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
    
    async def start(self, force_new_process: bool = False) -> Tuple[bool, str]:
        """Start the managed process or attach to an existing one.

        Args:
            force_new_process: If True, don't try to attach to existing processes
                               (used for restart operations)

        Returns:
            Tuple of (success, message).
        """
        if self.is_running:
            return True, "Process is already running"
            
        # First try to attach to an existing process if a port is configured
        # Skip this step if force_new_process is True (i.e., during restart)
        if self.config.port is not None and not force_new_process:
            success, message = self.attach_to_existing_process()
            if success:
                return success, message
            logger.info(f"No existing process found on port {self.config.port}, starting new process")
        
        # If force_new_process is True, we need to ensure the port is free
        # This is critical for restart operations
        if force_new_process and self.config.port is not None:
            # Check if there's any process using our target port
            port_pids = self._get_processes_using_port(self.config.port)
            if port_pids:
                logger.warning(f"Port {self.config.port} is in use by processes {port_pids} when attempting to start new process")
                # Try to force kill processes using the port
                port_cleared = await self._force_kill_port_processes()
                if not port_cleared:
                    return False, f"Failed to free port {self.config.port} for new process"
                logger.info(f"Successfully cleared port {self.config.port} for new process")
            
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
            if self.config.log_to_file:
                # Ensure we've set up the log file path
                if not hasattr(self, '_log_file_path'):
                    self._setup_log_file()
                
                # Create parent directories if needed (redundant but for safety)
                self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Close any existing log file handle
                if hasattr(self, '_log_file_handle') and self._log_file_handle and not self._log_file_handle.closed:
                    try:
                        self._log_file_handle.close()
                        logger.info(f"Closed existing log file handle before opening new one")
                    except Exception as e:
                        logger.error(f"Error closing existing log file handle: {str(e)}")
                
                # Open log file directly - this will be passed to the subprocess
                # so it will continue logging even if supervisor dies
                log_file_handle = open(self._log_file_path, 'w', encoding='utf-8')
                self._log_file_handle = log_file_handle
                logger.info(f"Opened log file for direct process output: {self._log_file_path}")    
            
                # Process writes directly to log file, supervisor doesn't capture
                stdout_dest = log_file_handle
                stderr_dest = subprocess.STDOUT
                
                # Log to our own logger that we're starting process with output to this file
                logger.info(f"Process will log output to: {self._log_file_path}")
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

    async def _verify_process_stopped(self, process: psutil.Process, timeout: float = 2.0) -> bool:
        """Verify that a process has been successfully stopped.
        
        Args:
            process: The psutil.Process object to check
            timeout: Maximum time to wait for verification in seconds
            
        Returns:
            True if process is confirmed stopped, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if process still exists
                if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                    return True
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                # Process no longer exists, which is what we want
                return True
                
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
            
        # If we're here, the process is still running after timeout
        return False
        
    def _get_processes_using_port(self, port: int) -> List[int]:
        """Find all processes using a specific port.
        
        Args:
            port: The port number to check
            
        Returns:
            List of process IDs using the port
        """
        if port is None:
            return []
            
        try:
            # Use subprocess to run netstat or ss command to check port usage
            if os.name == 'posix':
                # On Linux/Unix, use ss command which is more modern than netstat
                cmd = f"ss -tulpn | grep :{port} | awk '{{print $7}}' | grep -o 'pid=[0-9]*' | cut -d= -f2"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                pids = [int(pid.strip()) for pid in result.stdout.split() if pid.strip().isdigit()]
                
                # If ss didn't find anything, try with lsof as a backup
                if not pids:
                    cmd = f"lsof -i :{port} -t"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    pids = [int(pid.strip()) for pid in result.stdout.split() if pid.strip().isdigit()]
            else:
                # On Windows, use netstat
                cmd = f"netstat -ano | findstr :{port}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                pids = []
                for line in result.stdout.split('\n'):
                    if f":{port}" in line:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            try:
                                pids.append(int(parts[4]))
                            except ValueError:
                                pass
                                
            # Remove duplicates
            return list(set(pids))
        except Exception as e:
            logger.error(f"Error checking processes using port {port}: {e}")
            return []

    async def _kill_process_by_pid(self, pid: int, timeout: float = 5.0) -> bool:
        """Force kill a process by its PID.
        
        Args:
            pid: Process ID to kill
            timeout: Timeout for verification
            
        Returns:
            True if successfully killed, False otherwise
        """
        try:
            process = psutil.Process(pid)
            
            logger.warning(f"Force killing process {pid} to release port {self.config.port}")
            
            # First try graceful termination
            process.terminate()
            
            # Wait briefly for termination
            try:
                process.wait(timeout=2)
                return True
            except psutil.TimeoutExpired:
                # Force kill if still running
                process.kill()
                try:
                    process.wait(timeout=3)
                    return True
                except psutil.TimeoutExpired:
                    logger.error(f"Failed to kill process {pid} after multiple attempts")
                    return False
        except psutil.NoSuchProcess:
            # Process already gone
            return True
        except Exception as e:
            logger.error(f"Error killing process {pid}: {e}")
            return False

    async def _force_kill_port_processes(self) -> bool:
        """Force kill all processes using the configured port.
        
        Returns:
            True if successful, False otherwise
        """
        if self.config.port is None:
            return True
            
        logger.warning(f"Attempting to force kill all processes using port {self.config.port}")
        
        # Get all processes using the port
        pids = self._get_processes_using_port(self.config.port)
        
        if not pids:
            logger.info(f"No processes found using port {self.config.port}")
            return True
            
        # Kill each process
        kill_results = []
        for pid in pids:
            if pid == os.getpid():  # Skip our own process
                continue
                
            result = await self._kill_process_by_pid(pid)
            kill_results.append(result)
            
        # Verify the port is now free
        pids_after = self._get_processes_using_port(self.config.port)
        port_free = len(pids_after) == 0
        
        if not port_free:
            logger.error(f"Failed to free port {self.config.port}, still in use by: {pids_after}")
        
        return port_free

    async def _verify_port_released(self, timeout: float = 5.0) -> bool:
        """Verify that the configured port has been released after stopping a process.
        
        Args:
            timeout: Maximum time to wait for verification in seconds
            
        Returns:
            True if port is released or no port was configured, False if port is still in use
        """
        if self.config.port is None:
            return True
            
        start_time = time.time()
        while time.time() - start_time < timeout:
            # First check using our existing method
            if self._find_process_by_port() is None:
                # Do a secondary check with a different method to be sure
                pids = self._get_processes_using_port(self.config.port)
                if not pids:
                    logger.info(f"Port {self.config.port} is confirmed free")
                    return True
                else:
                    logger.warning(f"Port {self.config.port} still in use by PIDs: {pids}")
                    
            # Wait a bit before checking again
            await asyncio.sleep(0.2)
        
        # If we get here, the port is still in use after the timeout
        # Try to force kill any processes still using the port
        logger.warning(f"Port {self.config.port} still in use after timeout, attempting force kill")
        return await self._force_kill_port_processes()

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
            was_attached = self._process is None  # True if we attached to an existing process
            
            # First try to terminate the process normally
            logger.info(f"Stopping process with PID {self._pid}")
            
            # Terminate process group if on Unix-like system
            if os.name == 'posix':
                try:
                    # Get all child processes before terminating the parent
                    children = process.children(recursive=True)
                    
                    # First try to terminate the process group gracefully
                    os.killpg(os.getpgid(self._pid), signal.SIGTERM)
                    
                    # Wait for the main process to terminate
                    if not await self._verify_process_stopped(process, timeout=5.0):
                        # Force kill the process group if timeout
                        logger.warning(f"Process did not terminate gracefully, using SIGKILL")
                        os.killpg(os.getpgid(self._pid), signal.SIGKILL)
                    
                    # Ensure all children are terminated
                    for child in children:
                        try:
                            if child.is_running():
                                child.kill()
                        except psutil.NoSuchProcess:
                            pass
                except (ProcessLookupError, PermissionError) as e:
                    logger.warning(f"Error terminating process group: {str(e)}, falling back to direct termination")
                    # Fall back to regular process termination
                    process.terminate()
                    if not await self._verify_process_stopped(process, timeout=5.0):
                        process.kill()
            else:
                # On Windows, just terminate the process normally
                process.terminate()
                if not await self._verify_process_stopped(process, timeout=5.0):
                    process.kill()
                    
            # For attached processes or if a port is configured, verify the port is released
            if was_attached or self.config.port is not None:
                if not await self._verify_port_released(timeout=5.0):
                    logger.warning(f"Port {self.config.port} still in use after process termination")
                    # For attached processes, we might need a more aggressive approach
                    if was_attached:
                        # Try direct kill if the process is still running (could be a different process now)
                        pid = self._find_process_by_port()
                        if pid is not None:
                            logger.warning(f"Attempting to terminate process {pid} still using port {self.config.port}")
                            try:
                                kill_process = psutil.Process(pid)
                                kill_process.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                                logger.error(f"Failed to kill process on port {self.config.port}: {str(e)}")
                                return False, f"Failed to release port {self.config.port}"
                
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
            
            # Final verification that the process has been fully terminated
            if self.config.port is not None:
                # If we have a port, ensure it's been released
                port_released = await self._verify_port_released(timeout=1.0)
                if not port_released:
                    return False, f"Process appears stopped but port {self.config.port} is still in use"
            
            logger.info(f"Process successfully stopped")
            return True, "Process stopped"
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            # If the process no longer exists, that's actually a success for stopping
            if isinstance(e, psutil.NoSuchProcess):
                self._process = None
                self._pid = None
                return True, "Process no longer exists (already stopped)"
                
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
        return await self.start(force_new_process=True)

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
                await self.start(force_new_process=True)  # Force new process when auto-restarting
