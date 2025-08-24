import yaml
import logging
from pathlib import Path
from typing import Dict, Tuple, Any

class MetaRouter:
    """Pick agent + model for a task, estimate cost per request."""

    def __init__(self, cfg_path: str = "routing.yaml"):
        self.cfg_path = cfg_path
        self._load_config()
        
    def _load_config(self) -> None:
        """Load and validate routing configuration."""
        try:
            cfg_path = Path(self.cfg_path)
            if not cfg_path.exists():
                raise FileNotFoundError(f"Routing config not found: {cfg_path}")
                
            cfg = yaml.safe_load(cfg_path.read_text())
            
            # Parse default with better error handling
            default = cfg.get("default", "whisperer:mistral:7b")
            if ":" in default:
                # Format: "agent:model" or "model" (assume whisperer)
                parts = default.split(":")
                if len(parts) == 2:
                    self.default_agent, self.default_model = parts
                else:
                    # More than 2 parts, assume it's just a model name
                    self.default_agent = "whisperer"
                    self.default_model = default
            else:
                # Single string, could be agent or model
                self.default_agent = default
                self.default_model = None
                
            # Load rules with validation
            self.rules: Dict[str, Tuple[str, str | None, float]] = {}
            rules = cfg.get("rules", [])
            
            if not isinstance(rules, list):
                raise ValueError("'rules' must be a list")
                
            for i, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    logging.warning(f"Rule {i} is not a dictionary, skipping")
                    continue
                    
                task_type = rule.get("type")
                if not task_type:
                    logging.warning(f"Rule {i} missing 'type' field, skipping")
                    continue
                    
                agent = rule.get("agent")
                if not agent:
                    logging.warning(f"Rule {i} for task '{task_type}' missing 'agent' field, using default")
                    agent = self.default_agent
                    
                model = rule.get("model")
                if model == "None" or model is None:
                    model = None
                    
                cost = rule.get("cost", 0.0)
                try:
                    cost = float(cost)
                except (ValueError, TypeError):
                    logging.warning(f"Invalid cost for task '{task_type}': {cost}, using 0.0")
                    cost = 0.0
                    
                self.rules[task_type] = (agent, model, cost)
                
            logging.info(f"MetaRouter loaded {len(self.rules)} routing rules from {cfg_path}")
            
        except Exception as e:
            logging.error(f"Failed to load routing config: {e}")
            # Fallback configuration
            self.default_agent = "whisperer"
            self.default_model = "mistral:7b"
            self.rules = {}
            logging.warning("Using fallback routing configuration")

    def route(self, task: Dict) -> Tuple[str, str | None, float]:
        """Return (agent_name, llm_model, cost)."""
        t = task.get("type")
        agent, model, cost = self.rules.get(t, (self.default_agent, self.default_model, 0.0))
        return agent, model, cost
        
    def get_agent_name(self, task_type: str):
        """Legacy method for backward compatibility."""
        agent, _, _ = self.rules.get(task_type, (self.default_agent, self.default_model, 0.0))
        return agent