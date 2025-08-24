"""Basic sanity tests"""

def test_sanity():
    """Ensure basic Python functionality works"""
    assert True

def test_imports():
    """Test that we can import our modules"""
    try:
        from orchestrator.workflows.router import select_profile_for_role
        from memory.vector_store import VectorStore
        from memory.cache import CacheStore
        assert True
    except ImportError as e:
        assert False, f"Import failed: {e}"

def test_router_logic():
    """Test the model routing logic"""
    from orchestrator.workflows.router import select_profile_for_role
    
    profile = select_profile_for_role("doc_writer")
    assert profile is not None
    assert "model" in profile

def test_task_routing():
    """Test complete task routing"""
    from orchestrator.workflows.router import route_task
    
    task_data = {
        "role": "doc_writer",
        "priority": 1,
        "budget": "standard"
    }
    
    routing_result = route_task(task_data)
    assert routing_result["agent_role"] == "doc_writer"
    assert "model_config" in routing_result
    assert "routing_info" in routing_result
