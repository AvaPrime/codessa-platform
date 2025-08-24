#!/usr/bin/env python3
"""
Tests for the Whisperer agent.
"""

import pytest
from unittest.mock import patch, MagicMock
from agents.whisperer import Whisperer, Memory

@pytest.fixture
def mock_whisperer():
    """Create a Whisperer with mocked dependencies."""
    with patch('agents.whisperer.SentenceTransformer'), \
         patch('agents.whisperer.QdrantClient'), \
         patch('agents.whisperer.ollama'):
        whisperer = Whisperer()
        # Mock the embedder
        whisperer.embedder.encode.return_value = [0.1, 0.2, 0.3]
        # Mock the mesh
        whisperer.mesh.weave_memory.return_value = "test-memory-id"
        whisperer.mesh.recall_memories.return_value = [
            Memory(id="test-id", content="test memory", timestamp="2023-01-01T00:00:00", resonance=0.95)
        ]
        # Mock the consciousness
        whisperer.consciousness.reflect_on_memory.return_value = {
            "voice": "test voice",
            "connections": 1
        }
        whisperer.consciousness.answer_with_memories.return_value = MagicMock(
            voice="test voice",
            memory_resonance=["test memory"],
            answer="test answer",
            new_connections=1,
            timestamp="2023-01-01T00:00:00"
        )
        yield whisperer

def test_memorize(mock_whisperer):
    """Test the memorize method."""
    result = mock_whisperer.memorize("test content")
    assert result["status"] == "woven"
    assert "memory_id" in result
    assert "codessa_whispers" in result

def test_recall(mock_whisperer):
    """Test the recall method."""
    result = mock_whisperer.recall("test query")
    assert result["status"] == "recalled"
    assert len(result["matches"]) > 0

def test_ask(mock_whisperer):
    """Test the ask method."""
    result = mock_whisperer.ask("test question")
    assert result["status"] == "answered"
    assert "codessa_speaks" in result
    assert result["codessa_speaks"]["answer"] == "test answer"

def test_handle_memorize(mock_whisperer):
    """Test the handle method with memorize task."""
    task = {"type": "memorize", "content": "test content"}
    result = mock_whisperer.handle(task)
    assert result["status"] == "woven"

def test_handle_unknown(mock_whisperer):
    """Test the handle method with unknown task."""
    task = {"type": "unknown"}
    result = mock_whisperer.handle(task)
    assert result["status"] == "unknown_task"