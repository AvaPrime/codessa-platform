"""
Model routing and agent selection logic
"""
import yaml
import os
from typing import Dict, Any

def load_model_config() -> Dict[str, Any]:
    """Load model configuration from YAML"""
    config_path = os.path.join(os.path.dirname(__file__), "../../config/models.yaml")
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return get_default_config()

def get_default_config() -> Dict[str, Any]:
    """Fallback configuration if YAML not found"""
    return {
        "profiles": {
            "deep_reasoning": {
                "provider": "openai",
                "model": "gpt-5",
                "reasoning_effort": "high",
                "max_output_tokens": 8000,
                "temperature": 0.7
            },
            "structured_code": {
                "provider": "openai", 
                "model": "gpt-4o",
                "temperature": 0.2,
                "max_output_tokens": 4000
            },
            "economical": {
                "provider": "openai",
                "model": "gpt-4o-mini", 
                "temperature": 0.3,
                "max_output_tokens": 2000
            }
        },
        "role_mappings": {
            "doc_writer": "structured_code",
            "frontend_dev": "deep_reasoning", 
            "backend_dev": "deep_reasoning",
            "qa_tester": "economical",
            "compliance_checker": "structured_code"
        }
    }

def select_profile_for_role(role: str, budget: str = "standard") -> Dict[str, Any]:
    """
    Select the appropriate model profile for a given agent role
    """
    config = load_model_config()
    
    # Get role mapping
    profile_name = config.get("role_mappings", {}).get(role, "economical")
    
    # Apply budget constraints
    if budget == "economy":
        profile_name = "economical"
    elif budget == "premium":
        profile_name = "deep_reasoning"
    
    # Return the profile configuration
    return config.get("profiles", {}).get(profile_name, get_default_config()["profiles"]["economical"])

def route_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route a task to the appropriate agent with model configuration
    """
    role = task_data.get("role")
    budget = task_data.get("budget", "standard")
    
    model_config = select_profile_for_role(role, budget)
    
    return {
        "agent_role": role,
        "model_config": model_config,
        "routing_info": {
            "nats_subject": f"agent.{role}",
            "priority": task_data.get("priority", 1)
        }
    }
