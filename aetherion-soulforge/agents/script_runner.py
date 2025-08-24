#!/usr/bin/env python3
"""
Script Runner - Task Orchestration Agent

Implements a JSON DSL interpreter that executes a sequence of tasks
by passing them to the appropriate agents via the MetaRouter.
"""

from __future__ import annotations
import json
from typing import Dict, Any, List
from datetime import datetime

from .base import BaseAgent
from .metarouter import MetaRouter

class ScriptRunner(BaseAgent):
    """Executes a sequence of tasks defined in a JSON DSL format."""
    
    def __init__(self, agents: Dict[str, BaseAgent], router: MetaRouter):
        """
        Initialize the ScriptRunner with available agents and a router.
        
        Args:
            agents: Dictionary mapping agent names to agent instances
            router: MetaRouter instance for routing tasks to agents
        """
        self.agents = agents
        self.router = router
        
    def run_script(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a sequence of tasks defined in a script.
        
        Args:
            script: A dictionary containing a 'tasks' list with task definitions
            
        Returns:
            A dictionary containing the execution results and summary
        """
        if not isinstance(script, dict) or "tasks" not in script:
            return {
                "status": "error",
                "message": "Invalid script format. Expected a dictionary with a 'tasks' list.",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        tasks = script.get("tasks", [])
        if not tasks:
            return {
                "status": "error",
                "message": "No tasks defined in the script.",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        results = []
        summary = {
            "total_tasks": len(tasks),
            "successful_tasks": 0,
            "failed_tasks": 0,
            "start_time": datetime.utcnow().isoformat()
        }
        
        for i, task in enumerate(tasks):
            task_num = i + 1
            task_type = task.get("type", "unknown")
            
            try:
                # Get the appropriate agent for this task
                agent_name = self.router.get_agent_name(task_type)
                agent = self.agents.get(agent_name)
                
                if not agent:
                    task_result = {
                        "status": "error",
                        "task_num": task_num,
                        "task_type": task_type,
                        "message": f"No agent found for task type: {task_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    summary["failed_tasks"] += 1
                else:
                    # Execute the task with the appropriate agent
                    task_result = agent.handle(task)
                    task_result["task_num"] = task_num
                    task_result["task_type"] = task_type
                    task_result["timestamp"] = datetime.utcnow().isoformat()
                    
                    if task_result.get("status") in ["error", "unknown_task"]:
                        summary["failed_tasks"] += 1
                    else:
                        summary["successful_tasks"] += 1
            except Exception as e:
                task_result = {
                    "status": "error",
                    "task_num": task_num,
                    "task_type": task_type,
                    "message": f"Exception during task execution: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                summary["failed_tasks"] += 1
                
            results.append(task_result)
            
        summary["end_time"] = datetime.utcnow().isoformat()
        
        return {
            "status": "completed",
            "results": results,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a script execution task.
        
        Args:
            task: A dictionary containing:
                - type: Must be 'script'
                - script: A JSON string or dictionary with the script definition
                
        Returns:
            A dictionary containing the execution results
        """
        task_type = task.get("type")
        
        if task_type != "script":
            return {
                "status": "error",
                "message": f"ScriptRunner only handles 'script' tasks, got: {task_type}",
                "supported_tasks": ["script"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        script = task.get("script")
        if not script:
            return {
                "status": "error",
                "message": "No script provided in the task.",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        # If script is provided as a JSON string, parse it
        if isinstance(script, str):
            try:
                script = json.loads(script)
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "message": "Invalid JSON in script.",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        return self.run_script(script)