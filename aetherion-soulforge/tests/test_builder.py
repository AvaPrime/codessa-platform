#!/usr/bin/env python3
"""
Tests for the Builder agent.
"""

import pytest
from unittest.mock import patch, MagicMock
from agents.builder import Builder

@pytest.fixture
def mock_builder():
    """Create a Builder with mocked dependencies."""
    with patch('agents.builder.subprocess.run') as mock_run:
        # Mock the subprocess.run response
        mock_process = MagicMock()
        mock_process.stdout = "test output"
        mock_run.return_value = mock_process
        
        builder = Builder()
        yield builder

def test_build(mock_builder):
    """Test the build method."""
    result = mock_builder.build("test-repo", "test-tag")
    assert result == "test output"

def test_docker_run(mock_builder):
    """Test the docker_run method."""
    result = mock_builder.docker_run("test-repo", "test-tag", "8080")
    assert result == "test output"

def test_test(mock_builder):
    """Test the test method."""
    result = mock_builder.test("test-path")
    assert result == "test output"

def test_handle_build(mock_builder):
    """Test the handle method with build task."""
    task = {"type": "build", "repo": "test-repo", "tag": "test-tag"}
    result = mock_builder.handle(task)
    assert "stdout" in result
    assert result["stdout"] == "test output"

def test_handle_run(mock_builder):
    """Test the handle method with run task."""
    task = {"type": "run", "repo": "test-repo", "tag": "test-tag", "port": "8080"}
    result = mock_builder.handle(task)
    assert "stdout" in result
    assert result["stdout"] == "test output"

def test_handle_test(mock_builder):
    """Test the handle method with test task."""
    task = {"type": "test", "path": "test-path"}
    result = mock_builder.handle(task)
    assert "stdout" in result
    assert result["stdout"] == "test output"

def test_handle_unknown(mock_builder):
    """Test the handle method with unknown task."""
    task = {"type": "unknown"}
    result = mock_builder.handle(task)
    assert "status" in result
    assert result["status"] == "error"