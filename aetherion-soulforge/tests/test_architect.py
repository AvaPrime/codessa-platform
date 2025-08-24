#!/usr/bin/env python3
"""
Tests for the Architect agent.
"""

import pytest
from unittest.mock import patch, MagicMock
from agents.architect import Architect

@pytest.fixture
def mock_architect():
    """Create an Architect with mocked dependencies."""
    with patch('agents.architect.SentenceTransformer'), \
         patch('agents.architect.requests.post') as mock_post:
        # Mock the response from Ollama
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "test response"}
        mock_post.return_value = mock_response
        
        architect = Architect(llm_model="test-model")
        yield architect

def test_compose(mock_architect):
    """Test the compose method."""
    result = mock_architect.compose("@startuml\nclass Test\n@enduml")
    assert result == "test response"

def test_refactor(mock_architect, tmp_path):
    """Test the refactor method."""
    # Create a temporary file
    test_file = tmp_path / "test.py"
    test_file.write_text("def test(): pass")
    
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "def test(): pass"
        result = mock_architect.refactor(str(test_file), "Add docstring")
        assert result == "test response"

def test_handle_compose(mock_architect):
    """Test the handle method with compose task."""
    task = {"type": "compose", "diagram": "@startuml\nclass Test\n@enduml"}
    result = mock_architect.handle(task)
    assert "diagram" in result
    assert result["diagram"] == "test response"

def test_handle_refactor(mock_architect, tmp_path):
    """Test the handle method with refactor task."""
    # Create a temporary file
    test_file = tmp_path / "test.py"
    test_file.write_text("def test(): pass")
    
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "def test(): pass"
        task = {"type": "refactor", "path": str(test_file), "changes": "Add docstring"}
        result = mock_architect.handle(task)
        assert "patch" in result
        assert result["patch"] == "test response"

def test_handle_unknown(mock_architect):
    """Test the handle method with unknown task."""
    task = {"type": "unknown"}
    result = mock_architect.handle(task)
    assert "status" in result
    assert result["status"] == "error"