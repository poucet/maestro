"""Tests for the FileManager class."""

import os
from pathlib import Path
import pytest
import tempfile

from simply_maestro.core import FileManager


@pytest.fixture
def test_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def file_manager(test_dir):
    """Create a FileManager instance for testing."""
    return FileManager(allowed_paths=[test_dir])


@pytest.fixture
def test_file(test_dir):
    """Create a test file."""
    test_file = test_dir / "test.txt"
    test_file.write_text("Test content\nLine 2\nLine 3\n")
    return test_file


def test_read_file(file_manager, test_file):
    """Test reading a file."""
    success, content = file_manager.read_file(test_file)
    assert success, f"Failed to read file: {content}"
    assert content == "Test content\nLine 2\nLine 3\n"
    
    # Test reading non-existent file
    success, content = file_manager.read_file(test_file.parent / "nonexistent.txt")
    assert not success, "Should fail for non-existent file"


def test_write_file(file_manager, test_dir):
    """Test writing to a file."""
    test_file = test_dir / "new_file.txt"
    content = "New file content\nMultiple lines\n"
    
    success, message = file_manager.write_file(test_file, content)
    assert success, f"Failed to write file: {message}"
    assert test_file.exists(), "File should exist after writing"
    assert test_file.read_text() == content, "File content should match what was written"
    
    # Test writing to path outside allowed paths
    outside_path = Path("/tmp/outside.txt")
    success, message = file_manager.write_file(outside_path, "test")
    assert not success, "Should fail for path outside allowed paths"


def test_apply_diff(file_manager, test_file):
    """Test applying a diff to a file."""
    original = test_file.read_text()
    modified = "Test content\nModified line\nLine 3\nAdded line\n"
    
    success, message = file_manager.apply_diff(test_file, original, modified)
    assert success, f"Failed to apply diff: {message}"
    assert test_file.read_text() == modified, "File content should match the modified content"
    
    # Verify backup was created
    backup_file = test_file.with_suffix(".txt.bak")
    assert backup_file.exists(), "Backup file should exist"
    assert backup_file.read_text() == original, "Backup should contain original content"


def test_search_files(file_manager, test_dir):
    """Test searching for patterns in files.
    
    Note: This test is mocked as it would normally require ripgrep to be installed.
    """
    # Mock the subprocess.run used in search_files to avoid dependency on ripgrep
    import subprocess
    from unittest.mock import patch
    
    # Create some test files
    (test_dir / "file1.txt").write_text("Test content with pattern1\nAnother line\n")
    (test_dir / "file2.txt").write_text("Different content with pattern2\n")
    
    # Define a mock response similar to ripgrep JSON output
    mock_response = """
    {"type":"match","data":{"path":{"text":"file1.txt"},"lines":{"text":"Test content with pattern1"},"line_number":1}}
    {"type":"match","data":{"path":{"text":"file2.txt"},"lines":{"text":"Different content with pattern2"},"line_number":1}}
    """
    
    # Mock subprocess.run to return our fake ripgrep output
    mock_result = type('MockResult', (), {
        'returncode': 0,
        'stdout': mock_response,
        'stderr': ''
    })
    
    with patch.object(subprocess, 'run', return_value=mock_result):
        success, results = file_manager.search_files("pattern", test_dir)
        
        assert success, "Search should succeed"
        assert isinstance(results, list), "Results should be a list"
        assert len(results) == 2, "Should find 2 matches"
        assert results[0]["path"] == "file1.txt", "First match should be in file1.txt"
        assert "pattern1" in results[0]["content"], "Content should contain pattern1"
