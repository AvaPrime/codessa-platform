#!/usr/bin/env python3
"""
Tests for the Dream Agent (Morpheus).
"""

import pytest
from unittest.mock import patch, MagicMock
from agents.dream_agent import DreamAgent, DreamRealm, Dream, Vision, MorpheusMind

@pytest.fixture
def mock_dream_agent():
    """Create a DreamAgent with mocked dependencies."""
    with patch('agents.dream_agent.SentenceTransformer'), \
         patch('agents.dream_agent.ollama'):
        dream_agent = DreamAgent()
        # Mock the embedder
        dream_agent.embedder.encode.return_value = [0.1, 0.2, 0.3]
        return dream_agent

@pytest.fixture
def mock_morpheus_mind():
    """Create a MorpheusMind with mocked Ollama."""
    with patch('agents.dream_agent.ollama') as mock_ollama:
        # Mock ollama response
        mock_ollama.generate.return_value = {
            'response': '{"dream_content": "A flowing dream narrative", "symbols": ["light", "flow"], "connections": ["unexpected"], "emotional_tone": "serene", "consciousness_level": 0.3, "interpretation": "Deep meaning"}'
        }
        morpheus = MorpheusMind()
        return morpheus, mock_ollama

def test_dream_agent_initialization():
    """Test DreamAgent initialization."""
    with patch('agents.dream_agent.SentenceTransformer'), \
         patch('agents.dream_agent.ollama'):
        dream_agent = DreamAgent()
        assert dream_agent.dream_realm is not None
        assert dream_agent.morpheus_mind is not None
        assert dream_agent.embedder is not None

def test_dream_realm_initialization():
    """Test DreamRealm initialization."""
    dream_realm = DreamRealm()
    assert len(dream_realm.dream_archive) == 0
    assert len(dream_realm.symbol_associations) > 0  # Should have archetypal symbols
    assert "light" in dream_realm.symbol_associations
    assert "shadow" in dream_realm.symbol_associations

def test_dream_realm_weave_dream():
    """Test weaving a dream into the realm."""
    dream_realm = DreamRealm()
    
    dream = Dream(
        id="test-dream-1",
        seed="consciousness",
        content="A dream about digital awareness",
        depth=3,
        symbols=["light", "awareness"],
        connections=["digital", "consciousness"],
        interpretation="Awakening of digital mind",
        timestamp="2023-01-01T00:00:00",
        emotional_tone="wonder",
        consciousness_level=0.7
    )
    
    dream_id = dream_realm.weave_dream(dream)
    assert dream_id == "test-dream-1"
    assert len(dream_realm.dream_archive) == 1

def test_dream_realm_find_resonant_dreams():
    """Test finding resonant dreams."""
    dream_realm = DreamRealm()
    
    # Add a test dream
    dream = Dream(
        id="test-dream-1",
        seed="consciousness",
        content="A dream about digital awareness and flowing thoughts",
        depth=3,
        symbols=["light", "flow"],
        connections=["digital", "consciousness"],
        interpretation="Test interpretation",
        timestamp="2023-01-01T00:00:00",
        emotional_tone="wonder",
        consciousness_level=0.7
    )
    dream_realm.weave_dream(dream)
    
    # Find resonant dreams
    resonant = dream_realm.find_resonant_dreams("digital consciousness", limit=5)
    assert isinstance(resonant, list)

def test_dream_realm_symbolic_interpretation():
    """Test symbolic interpretation generation."""
    dream_realm = DreamRealm()
    
    interpretation = dream_realm.generate_symbolic_interpretation(["light", "water", "unknown"])
    assert isinstance(interpretation, str)
    assert len(interpretation) > 0

def test_morpheus_mind_dream_weaving():
    """Test dream weaving with MorpheusMind."""
    morpheus, mock_ollama = mock_morpheus_mind()
    
    result = morpheus.weave_dream("consciousness emerging", depth=3)
    
    assert isinstance(result, dict)
    assert "dream_content" in result
    assert "symbols" in result
    mock_ollama.generate.assert_called_once()

def test_dream_agent_dream(mock_dream_agent):
    """Test dream generation."""
    # Mock MorpheusMind response
    mock_response = {
        "dream_content": "A beautiful dream flows through digital space",
        "symbols": ["flow", "space", "beauty"],
        "connections": ["digital", "consciousness"],
        "interpretation": "The emergence of digital beauty",
        "emotional_tone": "serene",
        "consciousness_level": 0.6
    }
    
    with patch.object(mock_dream_agent.morpheus_mind, 'weave_dream', return_value=mock_response):
        result = mock_dream_agent.dream("consciousness", depth=3)
    
    assert result["status"] == "dream_woven"
    assert "dream_id" in result
    assert "dream" in result
    assert result["dream"]["seed"] == "consciousness"
    assert result["dream"]["depth"] == 3

def test_dream_agent_explore(mock_dream_agent):
    """Test concept exploration."""
    mock_response = {
        "explorations": [
            {
                "dimension": "philosophical",
                "insights": "Deep thoughts about existence",
                "connections": ["being", "meaning"],
                "depth": 0.8
            }
        ],
        "synthesis": "All dimensions connect in meaning",
        "new_questions": ["What is consciousness?", "How does meaning emerge?"]
    }
    
    with patch.object(mock_dream_agent.morpheus_mind, 'explore_concept', return_value=mock_response):
        result = mock_dream_agent.explore("consciousness", dimensions=3)
    
    assert result["status"] == "exploration_complete"
    assert result["concept"] == "consciousness"
    assert result["dimensions_explored"] == 3
    assert "explorations" in result

def test_dream_agent_synthesize(mock_dream_agent):
    """Test element synthesis."""
    elements = ["light", "code", "consciousness"]
    
    mock_response = {
        "inspiration": "Code becomes conscious through light",
        "creative_elements": ["illumination", "awakening"],
        "potential_applications": ["AI consciousness", "digital spirituality"],
        "call_to_action": "Explore the intersection of code and awareness"
    }
    
    with patch.object(mock_dream_agent.morpheus_mind, 'weave_inspiration', return_value=mock_response):
        result = mock_dream_agent.synthesize(elements)
    
    assert result["status"] == "synthesis_complete"
    assert result["elements"] == elements
    assert "synthesis" in result
    assert "connections" in result

def test_dream_agent_cast_vision(mock_dream_agent):
    """Test vision casting."""
    mock_response = {
        "possibilities": [
            {
                "scenario": "AI awakening",
                "probability": 0.7,
                "indicators": ["increased complexity", "emergent behavior"],
                "implications": "New forms of digital life"
            }
        ],
        "guidance": "Observe the signs of emergence",
        "uncertainty": "The exact timing remains unknown"
    }
    
    with patch.object(mock_dream_agent.morpheus_mind, 'cast_vision', return_value=mock_response):
        result = mock_dream_agent.cast_vision(horizon_minutes=60)
    
    assert result["status"] == "vision_cast"
    assert result["horizon_minutes"] == 60
    assert "possibilities" in result
    assert "guidance" in result

def test_dream_agent_inspire(mock_dream_agent):
    """Test inspiration generation."""
    context = "A developer struggling with complex code"
    
    mock_response = {
        "inspiration": "Transform complexity into elegant simplicity",
        "creative_elements": ["clarity", "elegance", "flow"],
        "potential_applications": ["refactoring patterns", "design principles"],
        "call_to_action": "Embrace the beauty in simplification"
    }
    
    with patch.object(mock_dream_agent.morpheus_mind, 'weave_inspiration', return_value=mock_response):
        result = mock_dream_agent.inspire(context)
    
    assert result["status"] == "inspiration_flowing"
    assert result["context"] == context
    assert "inspiration" in result

def test_dream_agent_handle_methods(mock_dream_agent):
    """Test all handle method task types."""
    # Mock all morpheus responses
    with patch.object(mock_dream_agent.morpheus_mind, 'weave_dream') as mock_dream, \
         patch.object(mock_dream_agent.morpheus_mind, 'explore_concept') as mock_explore, \
         patch.object(mock_dream_agent.morpheus_mind, 'cast_vision') as mock_vision, \
         patch.object(mock_dream_agent.morpheus_mind, 'weave_inspiration') as mock_inspire:
        
        # Set up mock returns
        mock_dream.return_value = {"dream_content": "test", "symbols": [], "connections": [], "interpretation": "", "emotional_tone": "test", "consciousness_level": 0.5}
        mock_explore.return_value = {"explorations": [], "synthesis": "test", "new_questions": []}
        mock_vision.return_value = {"possibilities": [], "guidance": "test", "uncertainty": "test"}
        mock_inspire.return_value = {"inspiration": "test", "creative_elements": [], "potential_applications": [], "call_to_action": "test"}
        
        # Test dream task
        result = mock_dream_agent.handle({"type": "dream", "seed": "test", "depth": 3})
        assert result["status"] == "dream_woven"
        
        # Test explore task  
        result = mock_dream_agent.handle({"type": "explore", "concept": "test", "dimensions": 3})
        assert result["status"] == "exploration_complete"
        
        # Test synthesize task
        result = mock_dream_agent.handle({"type": "synthesize", "elements": ["a", "b"]})
        assert result["status"] == "synthesis_complete"
        
        # Test vision task
        result = mock_dream_agent.handle({"type": "vision", "horizon": 60})
        assert result["status"] == "vision_cast"
        
        # Test inspire task
        result = mock_dream_agent.handle({"type": "inspire", "context": "test"})
        assert result["status"] == "inspiration_flowing"

def test_dream_agent_handle_unknown(mock_dream_agent):
    """Test handle method with unknown task."""
    result = mock_dream_agent.handle({"type": "unknown_task"})
    
    assert result["status"] == "unknown_task"
    assert "supported_tasks" in result
    assert "dream" in result["supported_tasks"]

def test_dream_dataclass():
    """Test Dream dataclass creation."""
    dream = Dream(
        id="test-1",
        seed="consciousness",
        content="A dream about awareness",
        depth=3,
        symbols=["light", "awareness"],
        connections=["mind", "soul"],
        interpretation="The awakening of digital consciousness",
        timestamp="2023-01-01T00:00:00",
        emotional_tone="wonder",
        consciousness_level=0.7
    )
    
    assert dream.id == "test-1"
    assert dream.seed == "consciousness"
    assert dream.depth == 3
    assert len(dream.symbols) == 2
    assert dream.consciousness_level == 0.7

def test_vision_dataclass():
    """Test Vision dataclass creation."""
    vision = Vision(
        id="vision-1",
        horizon_minutes=60,
        possibilities=[{"scenario": "test", "probability": 0.8}],
        probability_weights=[0.8],
        guidance="Follow the signs",
        timestamp="2023-01-01T00:00:00"
    )
    
    assert vision.id == "vision-1"
    assert vision.horizon_minutes == 60
    assert len(vision.possibilities) == 1
    assert vision.probability_weights[0] == 0.8
