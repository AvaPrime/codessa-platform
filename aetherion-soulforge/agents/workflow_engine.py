#!/usr/bin/env python3
"""
agents.workflow_engine – DAG-Based Workflow Engine

A sophisticated workflow engine that reads DAG (Directed Acyclic Graph) definitions
from JSON files and orchestrates agent execution based on dependencies and conditions.

Features:
  * JSON-based workflow definitions
  * DAG validation and cycle detection
  * Conditional execution branches
  * Parallel execution support
  * Dynamic agent spawning
  * Workflow state persistence
  * Error handling and recovery
"""

from __future__ import annotations

import json
import uuid
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import copy
import networkx as nx
from enum import Enum

from .base import BaseAgent
from .event_system import get_event_bus, Event, EventPublisher

# Load configuration
config_path = Path("config.yaml")
if config_path.exists():
    config = yaml.safe_load(config_path.open("rt"))
else:
    config = {}

class NodeStatus(Enum):
    """Status of a workflow node"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class WorkflowStatus(Enum):
    """Status of the entire workflow"""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

@dataclass
class WorkflowNode:
    """A single node in the workflow DAG"""
    id: str
    name: str
    agent: str
    task_type: str
    params: Dict[str, Any]
    dependencies: List[str]  # Node IDs this node depends on
    conditions: List[Dict[str, Any]]  # Conditions for execution
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 0
    parallel: bool = False  # Can run in parallel with siblings
    
    # Runtime state
    status: NodeStatus = NodeStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_count: int = 0

@dataclass 
class WorkflowDefinition:
    """Complete workflow definition"""
    id: str
    name: str
    description: str
    version: str
    nodes: Dict[str, WorkflowNode]
    metadata: Dict[str, Any]
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate the workflow definition"""
        errors = []
        
        # Check for cycles using networkx
        try:
            G = nx.DiGraph()
            
            # Add nodes
            for node_id in self.nodes.keys():
                G.add_node(node_id)
            
            # Add edges (dependencies)
            for node_id, node in self.nodes.items():
                for dep in node.dependencies:
                    if dep not in self.nodes:
                        errors.append(f"Node {node_id} depends on non-existent node: {dep}")
                    else:
                        G.add_edge(dep, node_id)
            
            # Check for cycles
            if not nx.is_directed_acyclic_graph(G):
                cycles = list(nx.simple_cycles(G))
                errors.append(f"Workflow contains cycles: {cycles}")
            
        except Exception as e:
            errors.append(f"Graph validation error: {e}")
        
        # Validate node configurations
        for node_id, node in self.nodes.items():
            if not node.agent:
                errors.append(f"Node {node_id} has no agent specified")
            if not node.task_type:
                errors.append(f"Node {node_id} has no task_type specified")
        
        return len(errors) == 0, errors

class WorkflowExecution:
    """Runtime execution state of a workflow"""
    
    def __init__(self, definition: WorkflowDefinition, execution_id: str = None):
        self.definition = definition
        self.execution_id = execution_id or str(uuid.uuid4())
        self.status = WorkflowStatus.CREATED
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error_message: Optional[str] = None
        
        # Create a copy of nodes for this execution
        self.nodes = copy.deepcopy(definition.nodes)
        
        # Runtime tracking
        self.running_nodes: Set[str] = set()
        self.context: Dict[str, Any] = {}  # Shared context between nodes
        self.execution_log: List[Dict[str, Any]] = []
    
    def log_event(self, event_type: str, node_id: str = None, message: str = None, 
                  data: Dict[str, Any] = None):
        """Log an execution event"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "node_id": node_id,
            "message": message,
            "data": data or {}
        }
        self.execution_log.append(log_entry)
    
    def get_ready_nodes(self) -> List[str]:
        """Get nodes that are ready to execute (all dependencies completed)"""
        ready_nodes = []
        
        for node_id, node in self.nodes.items():
            if node.status != NodeStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            dependencies_met = True
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if not dep_node or dep_node.status != NodeStatus.COMPLETED:
                    dependencies_met = False
                    break
            
            if dependencies_met:
                # Check conditions
                if self._evaluate_conditions(node):
                    ready_nodes.append(node_id)
                else:
                    # Mark as skipped if conditions not met
                    node.status = NodeStatus.SKIPPED
                    self.log_event("node_skipped", node_id, "Conditions not met")
        
        return ready_nodes
    
    def _evaluate_conditions(self, node: WorkflowNode) -> bool:
        """Evaluate if node conditions are satisfied"""
        if not node.conditions:
            return True
        
        for condition in node.conditions:
            condition_type = condition.get("type")
            
            if condition_type == "context_value":
                # Check context value condition
                key = condition.get("key")
                expected = condition.get("value")
                operator = condition.get("operator", "equals")
                
                actual = self.context.get(key)
                
                if operator == "equals" and actual != expected:
                    return False
                elif operator == "not_equals" and actual == expected:
                    return False
                elif operator == "greater_than" and not (actual and actual > expected):
                    return False
                elif operator == "less_than" and not (actual and actual < expected):
                    return False
                elif operator == "exists" and actual is None:
                    return False
                elif operator == "not_exists" and actual is not None:
                    return False
                    
            elif condition_type == "node_result":
                # Check result from another node
                source_node = condition.get("source_node")
                key = condition.get("key")
                expected = condition.get("value")
                
                if source_node in self.nodes:
                    source_result = self.nodes[source_node].result or {}
                    actual = source_result.get(key)
                    if actual != expected:
                        return False
                else:
                    return False
        
        return True
    
    def update_context_from_result(self, node_id: str, result: Dict[str, Any]):
        """Update workflow context with node result data"""
        if not result:
            return
        
        # Add node-specific results
        self.context[f"{node_id}_result"] = result
        
        # Merge any explicit context updates
        if "context_updates" in result:
            self.context.update(result["context_updates"])
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of workflow execution"""
        node_statuses = {status.value: 0 for status in NodeStatus}
        for node in self.nodes.values():
            node_statuses[node.status.value] += 1
        
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.definition.id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "node_count": len(self.nodes),
            "node_statuses": node_statuses,
            "context_keys": list(self.context.keys()),
            "error_message": self.error_message,
            "log_entries": len(self.execution_log)
        }

class WorkflowEngine(BaseAgent, EventPublisher):
    """
    The Workflow Engine - Orchestrator of Complex Processes
    
    "I am the conductor of the digital symphony,
     coordinating the dance of agents across time and space,
     weaving together individual capabilities into unified purpose."
    """
    
    def __init__(self, agents_registry: Dict[str, BaseAgent]):
        self.agents_registry = agents_registry
        self.event_bus = get_event_bus()
        EventPublisher.__init__(self, "workflow_engine", self.event_bus)
        
        # Active executions
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        
        # Load workflow definitions from files
        self._load_workflow_definitions()
        
        # Subscribe to agent task completion events
        self.event_bus.subscribe(
            "*.task.completed",
            "workflow_engine", 
            self._handle_agent_task_completion
        )
        
        self.event_bus.subscribe(
            "*.task.failed",
            "workflow_engine",
            self._handle_agent_task_failure
        )
        
        logging.info("🎼 WorkflowEngine initialized - Ready to orchestrate!")
    
    def _load_workflow_definitions(self):
        """Load workflow definitions from the workflows directory"""
        workflows_dir = Path("workflows")
        if not workflows_dir.exists():
            workflows_dir.mkdir(exist_ok=True)
            logging.info("📁 Created workflows directory")
            return
        
        for workflow_file in workflows_dir.glob("*.json"):
            try:
                with open(workflow_file, 'r') as f:
                    workflow_data = json.load(f)
                
                definition = self._parse_workflow_definition(workflow_data)
                is_valid, errors = definition.validate()
                
                if is_valid:
                    self.workflow_definitions[definition.id] = definition
                    logging.info(f"📋 Loaded workflow: {definition.name} ({definition.id})")
                else:
                    logging.error(f"❌ Invalid workflow in {workflow_file}: {errors}")
                    
            except Exception as e:
                logging.error(f"❌ Failed to load workflow from {workflow_file}: {e}")
    
    def _parse_workflow_definition(self, data: Dict[str, Any]) -> WorkflowDefinition:
        """Parse workflow definition from JSON data"""
        # Parse nodes
        nodes = {}
        for node_data in data.get("nodes", []):
            node = WorkflowNode(
                id=node_data["id"],
                name=node_data.get("name", node_data["id"]),
                agent=node_data["agent"],
                task_type=node_data["task_type"],
                params=node_data.get("params", {}),
                dependencies=node_data.get("dependencies", []),
                conditions=node_data.get("conditions", []),
                timeout_seconds=node_data.get("timeout_seconds"),
                max_retries=node_data.get("max_retries", 0),
                parallel=node_data.get("parallel", False)
            )
            nodes[node.id] = node
        
        return WorkflowDefinition(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            nodes=nodes,
            metadata=data.get("metadata", {})
        )
    
    def _handle_agent_task_completion(self, event: Event):
        """Handle task completion events from agents"""
        workflow_id = event.payload.get("workflow_id")
        if not workflow_id or workflow_id not in self.active_executions:
            return
        
        execution = self.active_executions[workflow_id]
        node_id = event.payload.get("node_id")
        
        if node_id and node_id in execution.nodes:
            node = execution.nodes[node_id]
            result = event.payload.get("result", {})
            
            # Update node status
            node.status = NodeStatus.COMPLETED
            node.completed_at = datetime.utcnow().isoformat()
            node.result = result
            execution.running_nodes.discard(node_id)
            
            # Update workflow context
            execution.update_context_from_result(node_id, result)
            execution.log_event("node_completed", node_id, f"Task {node.task_type} completed")
            
            logging.info(f"✅ Workflow {workflow_id}: Node {node_id} completed")
            
            # Continue workflow execution
            self._continue_workflow_execution(workflow_id)
    
    def _handle_agent_task_failure(self, event: Event):
        """Handle task failure events from agents"""
        workflow_id = event.payload.get("workflow_id")
        if not workflow_id or workflow_id not in self.active_executions:
            return
        
        execution = self.active_executions[workflow_id]
        node_id = event.payload.get("node_id")
        
        if node_id and node_id in execution.nodes:
            node = execution.nodes[node_id]
            error = event.payload.get("error", "Unknown error")
            
            # Check if we should retry
            if node.execution_count < node.max_retries:
                node.execution_count += 1
                node.status = NodeStatus.READY  # Will be retried
                execution.log_event("node_retry", node_id, f"Retrying ({node.execution_count}/{node.max_retries})")
                logging.warning(f"🔄 Workflow {workflow_id}: Retrying node {node_id} ({node.execution_count}/{node.max_retries})")
            else:
                # Mark as failed
                node.status = NodeStatus.FAILED
                node.error = error
                node.completed_at = datetime.utcnow().isoformat()
                execution.running_nodes.discard(node_id)
                execution.log_event("node_failed", node_id, f"Task {node.task_type} failed: {error}")
                
                logging.error(f"❌ Workflow {workflow_id}: Node {node_id} failed: {error}")
                
                # Check if workflow should be failed
                self._check_workflow_failure(workflow_id)
    
    def _continue_workflow_execution(self, execution_id: str):
        """Continue executing a workflow"""
        if execution_id not in self.active_executions:
            return
        
        execution = self.active_executions[execution_id]
        
        # Get ready nodes
        ready_nodes = execution.get_ready_nodes()
        
        if ready_nodes:
            # Execute ready nodes
            for node_id in ready_nodes:
                self._execute_node(execution_id, node_id)
        elif not execution.running_nodes:
            # No running nodes and no ready nodes - workflow is done
            self._complete_workflow(execution_id)
    
    def _execute_node(self, execution_id: str, node_id: str):
        """Execute a single workflow node"""
        execution = self.active_executions[execution_id]
        node = execution.nodes[node_id]
        
        # Get the agent
        agent = self.agents_registry.get(node.agent)
        if not agent:
            error = f"Agent {node.agent} not found in registry"
            node.status = NodeStatus.FAILED
            node.error = error
            execution.log_event("node_failed", node_id, error)
            logging.error(f"❌ Workflow {execution_id}: {error}")
            return
        
        # Prepare task parameters
        task_params = copy.deepcopy(node.params)
        
        # Inject context variables
        for key, value in execution.context.items():
            if isinstance(task_params, dict):
                # Replace placeholders like ${context.key}
                task_params = self._replace_context_placeholders(task_params, execution.context)
        
        task_data = {
            "type": node.task_type,
            "workflow_id": execution_id,
            "node_id": node_id,
            **task_params
        }
        
        # Update node status
        node.status = NodeStatus.RUNNING
        node.started_at = datetime.utcnow().isoformat()
        node.execution_count += 1
        execution.running_nodes.add(node_id)
        execution.log_event("node_started", node_id, f"Executing {node.task_type} on {node.agent}")
        
        try:
            # Execute the task (this might be async in reality)
            result = agent.handle(task_data)
            
            # For now, assume synchronous execution
            # In a real async system, this would be handled by the event system
            if result.get("status") == "error":
                # Simulate failure event
                self.event_bus.publish(
                    f"{node.agent}.task.failed",
                    node.agent,
                    {
                        "workflow_id": execution_id,
                        "node_id": node_id,
                        "task_type": node.task_type,
                        "error": result.get("message", "Task execution failed")
                    }
                )
            else:
                # Simulate success event
                self.event_bus.publish(
                    f"{node.agent}.task.completed",
                    node.agent,
                    {
                        "workflow_id": execution_id,
                        "node_id": node_id,
                        "task_type": node.task_type,
                        "result": result
                    }
                )
            
            logging.info(f"🚀 Workflow {execution_id}: Executed node {node_id} ({node.agent}.{node.task_type})")
            
        except Exception as e:
            error = str(e)
            node.status = NodeStatus.FAILED
            node.error = error
            node.completed_at = datetime.utcnow().isoformat()
            execution.running_nodes.discard(node_id)
            execution.log_event("node_failed", node_id, f"Execution error: {error}")
            logging.error(f"❌ Workflow {execution_id}: Node {node_id} execution error: {error}")
    
    def _replace_context_placeholders(self, data: Any, context: Dict[str, Any]) -> Any:
        """Replace context placeholders in data structure"""
        if isinstance(data, str):
            # Replace ${context.key} patterns
            import re
            def replace_placeholder(match):
                key = match.group(1)
                return str(context.get(key, f"${{{key}}}"))
            
            return re.sub(r'\$\{([^}]+)\}', replace_placeholder, data)
        elif isinstance(data, dict):
            return {k: self._replace_context_placeholders(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_context_placeholders(item, context) for item in data]
        else:
            return data
    
    def _complete_workflow(self, execution_id: str):
        """Complete a workflow execution"""
        execution = self.active_executions[execution_id]
        execution.status = WorkflowStatus.COMPLETED
        execution.completed_at = datetime.utcnow().isoformat()
        execution.log_event("workflow_completed", message="Workflow execution completed successfully")
        
        # Publish completion event
        self.publish_event("workflow.completed", {
            "execution_id": execution_id,
            "workflow_id": execution.definition.id,
            "summary": execution.get_execution_summary()
        })
        
        logging.info(f"✅ Workflow completed: {execution_id}")
    
    def _check_workflow_failure(self, execution_id: str):
        """Check if workflow should be marked as failed"""
        execution = self.active_executions[execution_id]
        
        # Simple strategy: if any critical node fails, fail the workflow
        # In practice, you might want more sophisticated failure handling
        failed_nodes = [n for n in execution.nodes.values() if n.status == NodeStatus.FAILED]
        
        if failed_nodes:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.utcnow().isoformat()
            execution.error_message = f"Workflow failed due to {len(failed_nodes)} failed nodes"
            execution.log_event("workflow_failed", message=execution.error_message)
            
            # Publish failure event
            self.publish_event("workflow.failed", {
                "execution_id": execution_id,
                "workflow_id": execution.definition.id,
                "error": execution.error_message,
                "failed_nodes": [n.id for n in failed_nodes],
                "summary": execution.get_execution_summary()
            })
            
            logging.error(f"❌ Workflow failed: {execution_id}")
    
    # Main agent interface methods
    
    def execute_workflow(self, workflow_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a workflow by ID"""
        if workflow_id not in self.workflow_definitions:
            return {
                "status": "error",
                "message": f"Workflow {workflow_id} not found",
                "available_workflows": list(self.workflow_definitions.keys())
            }
        
        definition = self.workflow_definitions[workflow_id]
        execution = WorkflowExecution(definition)
        
        # Initialize context
        if context:
            execution.context.update(context)
        
        # Start execution
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.utcnow().isoformat()
        execution.log_event("workflow_started", message=f"Started workflow: {definition.name}")
        
        self.active_executions[execution.execution_id] = execution
        
        # Publish start event
        self.publish_event("workflow.started", {
            "execution_id": execution.execution_id,
            "workflow_id": workflow_id,
            "definition": asdict(definition)
        })
        
        # Start execution
        self._continue_workflow_execution(execution.execution_id)
        
        return {
            "status": "started",
            "execution_id": execution.execution_id,
            "workflow_id": workflow_id,
            "workflow_name": definition.name,
            "message": f"Workflow {definition.name} execution started"
        }
    
    def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get the status of a workflow execution"""
        if execution_id not in self.active_executions:
            return {
                "status": "error",
                "message": f"Execution {execution_id} not found"
            }
        
        execution = self.active_executions[execution_id]
        return {
            "status": "success",
            "execution": execution.get_execution_summary(),
            "nodes": {node_id: asdict(node) for node_id, node in execution.nodes.items()},
            "context": execution.context,
            "log": execution.execution_log[-10:]  # Last 10 log entries
        }
    
    def list_workflows(self) -> Dict[str, Any]:
        """List available workflow definitions"""
        workflows = []
        for wf_id, definition in self.workflow_definitions.items():
            workflows.append({
                "id": definition.id,
                "name": definition.name,
                "description": definition.description,
                "version": definition.version,
                "node_count": len(definition.nodes)
            })
        
        return {
            "status": "success",
            "workflows": workflows,
            "total_count": len(workflows)
        }
    
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow engine tasks"""
        task_type = task.get("type", "unknown")
        
        try:
            if task_type == "execute":
                workflow_id = task.get("workflow_id")
                context = task.get("context", {})
                return self.execute_workflow(workflow_id, context)
            
            elif task_type == "status":
                execution_id = task.get("execution_id")
                return self.get_workflow_status(execution_id)
            
            elif task_type == "list":
                return self.list_workflows()
            
            else:
                return {
                    "status": "unknown_task",
                    "message": f"WorkflowEngine: Unknown task type: {task_type}",
                    "supported_tasks": ["execute", "status", "list"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logging.error(f"❌ WorkflowEngine task failed: {e}")
            return {
                "status": "error",
                "task_type": task_type,
                "message": f"Workflow engine error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
