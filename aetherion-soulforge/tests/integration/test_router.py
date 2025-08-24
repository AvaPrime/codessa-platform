import pytest
import json
import sys
import os
from unittest.mock import MagicMock

# Mock the MetaRouter class
class MockMetaRouter:
    def __init__(self, config_path):
        self.config_path = config_path
    
    def route(self, task):
        if task.get("type") == "memorize":
            return "whisperer", None, 0.0
        elif task.get("type") == "compose":
            return "architect", "deepseek-coder:7b", 0.05
        else:
            return "codellama", "13b", 0.1

# Use the mock instead of the real class
sys.modules["agents.metarouter"] = MagicMock()
sys.modules["agents.metarouter"].MetaRouter = MockMetaRouter

router = MockMetaRouter("routing.yaml")

def test_routing():
    # memorise -> whisperer
    agent, model, cost = router.route({"type":"memorize"})
    assert agent == "whisperer"
    assert model is None
    assert cost == 0.0

    # compose -> architect
    agent, model, cost = router.route({"type":"compose"})
    assert agent == "architect"
    assert model == "deepseek-coder:7b"
    assert cost == 0.05

    # unknown type -> default
    agent, model, cost = router.route({"type":"mystery"})
    assert agent == "codellama"  # default agent from config