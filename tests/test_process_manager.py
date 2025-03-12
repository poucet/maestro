"""Tests for the ProcessManager class."""

import asyncio
import os
from pathlib import Path
import pytest
import tempfile
import time

from supervisor.core import ProcessManager
from supervisor.core.process_manager import ProcessConfig


@pytest.fixture
def test_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def process_config(test_dir):
    """Create a test process configuration."""
    # Command that echoes a message and sleeps
    cmd = "python -c \"import time; print('Test process started'); time.sleep(10)\""
    return ProcessConfig(
        command=cmd,
        working_dir=test_dir,
        capture_output=True,
    )


@pytest.mark.asyncio
async def test_process_start_stop(process_config):
    """Test starting and stopping a process."""
    # Create process manager
    manager = ProcessManager(process_config)
    
    # Start process
    success, message = await manager.start()
    assert success, f"Failed to start process: {message}"
    assert manager.is_running, "Process should be running"
    
    # Allow time for process to start
    await asyncio.sleep(0.5)
    
    # Stop process
    success, message = await manager.stop()
    assert success, f"Failed to stop process: {message}"
    assert not manager.is_running, "Process should not be running"


@pytest.mark.asyncio
async def test_process_restart(process_config):
    """Test restarting a process."""
    # Create process manager
    manager = ProcessManager(process_config)
    
    # Start process
    success, message = await manager.start()
    assert success, f"Failed to start process: {message}"
    assert manager.is_running, "Process should be running"
    
    # Store the PID
    pid = manager._pid
    
    # Restart process
    success, message = await manager.restart()
    assert success, f"Failed to restart process: {message}"
    assert manager.is_running, "Process should be running after restart"
    
    # Check if PID changed (indication of restart)
    assert pid != manager._pid, "Process PID should change after restart"
    
    # Stop process
    await manager.stop()
