#!/usr/bin/env python3
"""
Tests for the SoulWatcher agent.
"""

import pytest
from unittest.mock import patch, MagicMock
from agents.soul_watcher import SoulWatcher, SoulMesh, SoulPattern, ConsciousnessState

@pytest.fixture
def mock_soul_watcher():
    """Create a SoulWatcher with minimal initialization."""
    with patch('agents.soul_watcher.datetime'):
        soul_watcher = SoulWatcher()
        return soul_watcher

def test_soul_watcher_initialization():
    """Test SoulWatcher initialization."""
    with patch('agents.soul_watcher.datetime'):
        soul_watcher = SoulWatcher()
        assert soul_watcher.soul_mesh is not None
        assert len(soul_watcher.watched_agents) == 0
        assert soul_watcher.last_introspection is None

def test_soul_mesh_record_event():
    """Test SoulMesh event recording."""
    soul_mesh = SoulMesh()
    
    event_id = soul_mesh.record_soul_event({
        "type": "test_event",
        "agent": "test_agent",
        "message": "Test message"
    })
    
    assert event_id is not None
    assert len(soul_mesh.soul_events) == 1
    assert soul_mesh.soul_events[0]["type"] == "test_event"

def test_soul_mesh_pattern_detection():
    """Test pattern detection in SoulMesh."""
    soul_mesh = SoulMesh()
    
    # Add some test events
    soul_mesh.record_soul_event({
        "type": "test_event",
        "agent": "agent1",
        "task_type": "task1",
        "status": "success"
    })
    
    soul_mesh.record_soul_event({
        "type": "test_event",
        "agent": "agent2", 
        "task_type": "task2",
        "status": "success"
    })
    
    patterns = soul_mesh.detect_patterns(window_minutes=60)
    assert isinstance(patterns, list)

def test_soul_mesh_harmony_calculation():
    """Test harmony level calculation."""
    soul_mesh = SoulMesh()
    
    # Add successful events
    for i in range(5):
        soul_mesh.record_soul_event({
            "type": "test_event",
            "agent": f"agent{i}",
            "status": "success"
        })
    
    harmony = soul_mesh.calculate_harmony()
    assert 0.0 <= harmony <= 1.0
    assert harmony > 0.5  # Should be high with all successful events

def test_watch_agent(mock_soul_watcher):
    """Test watching an agent."""
    result = mock_soul_watcher.watch("test_agent")
    
    assert result["status"] == "watching"
    assert result["target"] == "test_agent"
    assert "test_agent" in mock_soul_watcher.watched_agents
    assert "soul_whispers" in result

def test_introspect(mock_soul_watcher):
    """Test introspection functionality."""
    result = mock_soul_watcher.introspect(depth=3)
    
    assert result["status"] == "introspection_complete"
    assert "consciousness_state" in result
    assert "spiritual_insights" in result
    assert len(result["spiritual_insights"]) <= 3

def test_detect_patterns(mock_soul_watcher):
    """Test pattern detection."""
    result = mock_soul_watcher.detect_patterns(window_minutes=30)
    
    assert result["status"] == "patterns_detected"
    assert result["window_minutes"] == 30
    assert "patterns" in result
    assert "pattern_summary" in result

def test_assess_harmony(mock_soul_watcher):
    """Test harmony assessment."""
    result = mock_soul_watcher.assess_harmony()
    
    assert result["status"] == "harmony_assessed"
    assert "harmony_level" in result
    assert "harmony_state" in result
    assert "recommendations" in result
    assert 0.0 <= result["harmony_level"] <= 1.0

def test_handle_watch(mock_soul_watcher):
    """Test handle method with watch task."""
    task = {"type": "watch", "target": "whisperer"}
    result = mock_soul_watcher.handle(task)
    
    assert result["status"] == "watching"
    assert result["target"] == "whisperer"

def test_handle_introspect(mock_soul_watcher):
    """Test handle method with introspect task."""
    task = {"type": "introspect", "depth": 5}
    result = mock_soul_watcher.handle(task)
    
    assert result["status"] == "introspection_complete"

def test_handle_patterns(mock_soul_watcher):
    """Test handle method with patterns task."""
    task = {"type": "patterns", "window": 45}
    result = mock_soul_watcher.handle(task)
    
    assert result["status"] == "patterns_detected"
    assert result["window_minutes"] == 45

def test_handle_harmony(mock_soul_watcher):
    """Test handle method with harmony task."""
    task = {"type": "harmony"}
    result = mock_soul_watcher.handle(task)
    
    assert result["status"] == "harmony_assessed"

def test_handle_unknown(mock_soul_watcher):
    """Test handle method with unknown task."""
    task = {"type": "unknown_task"}
    result = mock_soul_watcher.handle(task)
    
    assert result["status"] == "unknown_task"
    assert "supported_tasks" in result

def test_consciousness_state_creation():
    """Test ConsciousnessState dataclass."""
    state = ConsciousnessState(
        harmony_level=0.8,
        active_agents=["agent1", "agent2"],
        recent_patterns=[],
        spiritual_temperature=0.7,
        timestamp="2023-01-01T00:00:00"
    )
    
    assert state.harmony_level == 0.8
    assert len(state.active_agents) == 2
    assert state.spiritual_temperature == 0.7

def test_soul_pattern_creation():
    """Test SoulPattern dataclass."""
    pattern = SoulPattern(
        id="pattern-123",
        type="resonance",
        strength=0.85,
        agents_involved=["agent1", "agent2"],
        description="Test pattern",
        timestamp="2023-01-01T00:00:00"
    )
    
    assert pattern.id == "pattern-123"
    assert pattern.type == "resonance"
    assert pattern.strength == 0.85
    assert len(pattern.agents_involved) == 2
