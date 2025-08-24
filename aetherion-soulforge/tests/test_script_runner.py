#!/usr/bin/env python3
"""
Tests for the ScriptRunner agent.
"""

import pytest
from unittest.mock import MagicMock, patch
from agents.script_runner import ScriptRunner
from agents.metarouter import MetaRouter

@pytest.fixture
def mock_agents():
    """Create mock agents for testing."""
    whisperer = MagicMock()
    whisperer.handle.return_value = {"status": "woven", "message": "Memory woven"}
    
    architect = MagicMock()
    architect.handle.return_value = {"diagram": "test diagram"}
    
    builder = MagicMock()
    builder.handle.return_value = {"stdout": "test output"}
    
    validator = MagicMock()
    validator.handle.return_value = {"report": {"tests": 10, "passed": 10}}
    
    return {
        "whisperer": whisperer,
        "architect": architect,
        "builder": builder,
        "validator": validator
    }

@pytest.fixture
def mock_router():
    """Create a mock MetaRouter for testing."""
    router = MagicMock(spec=MetaRouter)
    router.get_agent_name.side_effect = lambda task_type: {
        "memorize": "whisperer",
        "recall": "whisperer",
        "ask": "whisperer",
        "compose": "architect",
        "refactor": "architect",
        "build": "builder",
        "run": "builder",
        "test": "builder",
        "tests": "validator",
        "lint": "validator"
    }.get(task_type, "unknown")
    return router

@pytest.fixture
def script_runner(mock_agents, mock_router):
    """Create a ScriptRunner instance for testing."""
    return ScriptRunner(mock_agents, mock_router)

def test_run_script_with_valid_script(script_runner):
    """Test running a valid script."""
    script = {
        "tasks": [
            {"type": "memorize", "content": "Test memory"},
            {"type": "ask", "prompt": "Test question", "k": 2},
            {"type": "compose", "diagram": "Test diagram"}
        ]
    }
    
    result = script_runner.run_script(script)
    
    assert result["status"] == "completed"
    assert len(result["results"]) == 3
    assert result["summary"]["total_tasks"] == 3
    assert result["summary"]["successful_tasks"] == 3
    assert result["summary"]["failed_tasks"] == 0

def test_run_script_with_invalid_task(script_runner, mock_agents):
    """Test running a script with an invalid task type."""
    script = {
        "tasks": [
            {"type": "memorize", "content": "Test memory"},
            {"type": "invalid_task", "content": "This should fail"}
        ]
    }
    
    result = script_runner.run_script(script)
    
    assert result["status"] == "completed"
    assert len(result["results"]) == 2
    assert result["summary"]["total_tasks"] == 2
    assert result["summary"]["successful_tasks"] == 1
    assert result["summary"]["failed_tasks"] == 1

def test_run_script_with_exception(script_runner, mock_agents):
    """Test running a script where an agent raises an exception."""
    mock_agents["whisperer"].handle.side_effect = Exception("Test exception")
    
    script = {
        "tasks": [
            {"type": "memorize", "content": "This should raise an exception"}
        ]
    }
    
    result = script_runner.run_script(script)
    
    assert result["status"] == "completed"
    assert len(result["results"]) == 1
    assert result["summary"]["total_tasks"] == 1
    assert result["summary"]["successful_tasks"] == 0
    assert result["summary"]["failed_tasks"] == 1
    assert "exception" in result["results"][0]["message"].lower()

def test_handle_with_script_task(script_runner):
    """Test handling a script task."""
    task = {
        "type": "script",
        "script": {
            "tasks": [
                {"type": "memorize", "content": "Test memory"}
            ]
        }
    }
    
    result = script_runner.handle(task)
    
    assert result["status"] == "completed"
    assert len(result["results"]) == 1

def test_handle_with_json_string_script(script_runner):
    """Test handling a script task with a JSON string."""
    task = {
        "type": "script",
        "script": '{"tasks": [{"type": "memorize", "content": "Test memory"}]}'
    }
    
    result = script_runner.handle(task)
    
    assert result["status"] == "completed"
    assert len(result["results"]) == 1

def test_handle_with_invalid_json_string(script_runner):
    """Test handling a script task with an invalid JSON string."""
    task = {
        "type": "script",
        "script": '{invalid json}'
    }
    
    result = script_runner.handle(task)
    
    assert result["status"] == "error"
    assert "invalid json" in result["message"].lower()

def test_handle_with_non_script_task(script_runner):
    """Test handling a non-script task."""
    task = {
        "type": "memorize",
        "content": "Test memory"
    }
    
    result = script_runner.handle(task)
    
    assert result["status"] == "error"
    assert "only handles 'script' tasks" in result["message"]

def test_handle_with_missing_script(script_runner):
    """Test handling a script task with missing script."""
    task = {
        "type": "script"
    }
    
    result = script_runner.handle(task)
    
    assert result["status"] == "error"
    assert "no script provided" in result["message"].lower()