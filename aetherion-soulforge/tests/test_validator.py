#!/usr/bin/env python3
"""
Tests for the Validator agent.
"""

import pytest
from unittest.mock import patch, MagicMock
from agents.validator import Validator

@pytest.fixture
def mock_validator():
    """Create a Validator with mocked dependencies."""
    with patch('agents.validator.subprocess.run') as mock_run:
        # Mock the subprocess.run response
        mock_process = MagicMock()
        mock_process.stdout = "test stdout"
        mock_process.stderr = "test stderr"
        mock_run.return_value = mock_process
        
        validator = Validator()
        yield validator

def test_run_tests(mock_validator):
    """Test the run_tests method."""
    with patch('builtins.open', create=True) as mock_open, \
         patch('json.loads') as mock_loads:
        mock_open.return_value.__enter__.return_value.read.return_value = "{}"
        mock_loads.return_value = {"tests": 10, "passed": 8}
        result = mock_validator.run_tests("test-path")
        assert result["tests"] == 10
        assert result["passed"] == 8

def test_run_tests_exception(mock_validator):
    """Test the run_tests method with exception."""
    with patch('builtins.open', create=True) as mock_open:
        mock_open.side_effect = Exception("File not found")
        result = mock_validator.run_tests("test-path")
        assert "raw_output" in result
        assert "test stdout" in result["raw_output"]

def test_lint(mock_validator):
    """Test the lint method."""
    result = mock_validator.lint("test-path")
    assert "test stdout" in result
    assert "test stderr" in result

def test_handle_tests(mock_validator):
    """Test the handle method with tests task."""
    with patch.object(mock_validator, 'run_tests') as mock_run_tests:
        mock_run_tests.return_value = {"tests": 10, "passed": 8}
        task = {"type": "tests", "path": "test-path"}
        result = mock_validator.handle(task)
        assert "report" in result
        assert result["report"]["tests"] == 10
        assert result["report"]["passed"] == 8

def test_handle_lint(mock_validator):
    """Test the handle method with lint task."""
    with patch.object(mock_validator, 'lint') as mock_lint:
        mock_lint.return_value = "test lint output"
        task = {"type": "lint", "path": "test-path"}
        result = mock_validator.handle(task)
        assert "lint_report" in result
        assert result["lint_report"] == "test lint output"

def test_handle_unknown(mock_validator):
    """Test the handle method with unknown task."""
    task = {"type": "unknown"}
    result = mock_validator.handle(task)
    assert "status" in result
    assert result["status"] == "error"