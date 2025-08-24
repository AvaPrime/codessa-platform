#!/usr/bin/env python3
"""
Configuration Validation Utility

Validates that all referenced models and agents exist in the configuration files,
and that the routing configuration is consistent with the main config.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple


class ConfigValidator:
    """Validates Aetherion configuration files for consistency and completeness."""
    
    def __init__(self, config_path: str = "config.yaml", routing_path: str = "routing.yaml"):
        self.config_path = Path(config_path)
        self.routing_path = Path(routing_path)
        self.config = {}
        self.routing = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def load_configs(self) -> bool:
        """Load configuration files and return True if successful."""
        try:
            if self.config_path.exists():
                self.config = yaml.safe_load(self.config_path.read_text())
            else:
                self.errors.append(f"Config file not found: {self.config_path}")
                return False
                
            if self.routing_path.exists():
                self.routing = yaml.safe_load(self.routing_path.read_text())
            else:
                self.errors.append(f"Routing file not found: {self.routing_path}")
                return False
                
            return True
            
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error loading configs: {e}")
            return False
            
    def validate_models(self) -> None:
        """Validate that all referenced models are consistent between configs."""
        # Extract models from main config
        config_models = set()
        if "ollama" in self.config and "models" in self.config["ollama"]:
            config_models.update(self.config["ollama"]["models"].values())
            
        # Extract models from routing config
        routing_models = set()
        if "rules" in self.routing:
            for rule in self.routing["rules"]:
                if rule.get("model") and rule["model"] != "None":
                    routing_models.add(rule["model"])
                    
        # Check default model
        default_model = self.routing.get("default")
        if default_model:
            routing_models.add(default_model)
            
        # Find inconsistencies
        missing_in_config = routing_models - config_models
        unused_in_routing = config_models - routing_models
        
        if missing_in_config:
            self.errors.extend([
                f"Model '{model}' referenced in routing but not defined in config.yaml"
                for model in missing_in_config
            ])
            
        if unused_in_routing:
            self.warnings.extend([
                f"Model '{model}' defined in config.yaml but not used in routing"
                for model in unused_in_routing
            ])
            
    def validate_agents(self) -> None:
        """Validate that all referenced agents exist."""
        # Known agents from the codebase
        known_agents = {
            "whisperer", "architect", "builder", "validator", 
            "script_runner", "metarouter"
        }
        
        # Extract agents from routing config
        routing_agents = set()
        if "rules" in self.routing:
            for rule in self.routing["rules"]:
                if "agent" in rule:
                    routing_agents.add(rule["agent"])
                    
        # Extract agents from main config routing section
        config_agents = set()
        if "routing" in self.config:
            config_agents.update(self.config["routing"].values())
            
        all_referenced_agents = routing_agents | config_agents
        unknown_agents = all_referenced_agents - known_agents
        
        if unknown_agents:
            self.errors.extend([
                f"Unknown agent '{agent}' referenced in configuration"
                for agent in unknown_agents
            ])
            
    def validate_task_types(self) -> None:
        """Validate that task types are consistent between configs."""
        # Extract task types from main config routing
        config_tasks = set()
        if "routing" in self.config:
            config_tasks.update(self.config["routing"].keys())
            config_tasks.discard("default")  # Remove default key
            
        # Extract task types from routing rules
        routing_tasks = set()
        if "rules" in self.routing:
            for rule in self.routing["rules"]:
                if "type" in rule:
                    routing_tasks.add(rule["type"])
                    
        # Find inconsistencies
        missing_in_routing = config_tasks - routing_tasks
        missing_in_config = routing_tasks - config_tasks
        
        if missing_in_routing:
            self.warnings.extend([
                f"Task type '{task}' in config.yaml routing but not in routing.yaml rules"
                for task in missing_in_routing
            ])
            
        if missing_in_config:
            self.warnings.extend([
                f"Task type '{task}' in routing.yaml rules but not in config.yaml routing"
                for task in missing_in_config
            ])
            
    def validate_service_urls(self) -> None:
        """Validate that service URLs are properly formatted."""
        services = {
            "qdrant": self.config.get("qdrant", {}).get("url"),
            "ollama": self.config.get("ollama", {}).get("url")
        }
        
        for service_name, url in services.items():
            if url:
                if not url.startswith(("http://", "https://")):
                    self.errors.append(
                        f"Invalid {service_name} URL '{url}': must start with http:// or https://"
                    )
            else:
                self.warnings.append(f"No URL configured for {service_name} service")
                
    def validate_budget_config(self) -> None:
        """Validate budget configuration."""
        budget_config = self.config.get("budget", {})
        
        if "daily_limit_usd" in budget_config:
            limit = budget_config["daily_limit_usd"]
            if not isinstance(limit, (int, float)) or limit <= 0:
                self.errors.append(
                    f"Invalid budget daily_limit_usd: {limit}. Must be a positive number."
                )
        else:
            self.warnings.append("No budget.daily_limit_usd configured, using default of 1.0")
            
    def validate_routing_costs(self) -> None:
        """Validate that routing rules have reasonable cost estimates."""
        if "rules" not in self.routing:
            return
            
        for rule in self.routing["rules"]:
            cost = rule.get("cost", 0.0)
            
            if not isinstance(cost, (int, float)):
                self.errors.append(
                    f"Invalid cost for task '{rule.get('type')}': {cost}. Must be a number."
                )
            elif cost < 0:
                self.errors.append(
                    f"Negative cost for task '{rule.get('type')}': {cost}. Must be non-negative."
                )
            elif cost > 10.0:  # Arbitrary high threshold
                self.warnings.append(
                    f"High cost for task '{rule.get('type')}': {cost}. Consider reviewing."
                )
                
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validations and return (success, errors, warnings)."""
        self.errors.clear()
        self.warnings.clear()
        
        if not self.load_configs():
            return False, self.errors, self.warnings
            
        self.validate_models()
        self.validate_agents()
        self.validate_task_types()
        self.validate_service_urls()
        self.validate_budget_config()
        self.validate_routing_costs()
        
        success = len(self.errors) == 0
        return success, self.errors, self.warnings
        
    def print_report(self) -> None:
        """Print a formatted validation report."""
        success, errors, warnings = self.validate_all()
        
        print("🔍 Aetherion Configuration Validation Report")
        print("=" * 50)
        
        if success:
            print("✅ Configuration validation passed!")
        else:
            print("❌ Configuration validation failed!")
            
        if errors:
            print(f"\n🚨 Errors ({len(errors)}):")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
                
        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
                
        if not errors and not warnings:
            print("\n🎉 No issues found! Configuration looks perfect.")
            
        return success


def main():
    """CLI entry point for configuration validation."""
    import sys
    
    validator = ConfigValidator()
    success = validator.print_report()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
