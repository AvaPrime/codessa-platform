#!/usr/bin/env python3
"""
agents.event_system – Event Publishing and Subscription System

A unified event system that enables agents to publish and subscribe to events,
facilitating complex workflows and inter-agent communication patterns.

This system supports:
  * Event publishing with structured payloads
  * Topic-based subscriptions
  * Event filtering and routing
  * Async event handling
  * Event persistence and replay
"""

from __future__ import annotations

import json
import uuid
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
from pathlib import Path
import yaml
import threading
from queue import Queue, Empty
import time

# Load configuration
config_path = Path("config.yaml")
if config_path.exists():
    config = yaml.safe_load(config_path.open("rt"))
else:
    config = {}

@dataclass
class Event:
    """A single event in the system"""
    id: str
    topic: str
    source: str  # Agent that published the event
    payload: Dict[str, Any]
    timestamp: str
    metadata: Dict[str, Any]
    priority: int = 0  # Higher number = higher priority
    ttl_seconds: Optional[int] = None  # Time to live

    def is_expired(self) -> bool:
        """Check if the event has expired based on TTL"""
        if self.ttl_seconds is None:
            return False
        
        event_time = datetime.fromisoformat(self.timestamp)
        return datetime.utcnow() - event_time > timedelta(seconds=self.ttl_seconds)

@dataclass
class Subscription:
    """A subscription to events on a topic"""
    id: str
    subscriber: str  # Agent name
    topic_pattern: str  # Can use wildcards like "agent.*" or "workflow.completed"
    handler: Callable[[Event], None]
    filter_func: Optional[Callable[[Event], bool]] = None
    active: bool = True

    def matches_topic(self, topic: str) -> bool:
        """Check if this subscription matches the given topic"""
        if self.topic_pattern == "*":
            return True
        
        if "*" in self.topic_pattern:
            # Simple wildcard matching
            pattern_parts = self.topic_pattern.split(".")
            topic_parts = topic.split(".")
            
            if len(pattern_parts) != len(topic_parts):
                return False
            
            for pattern_part, topic_part in zip(pattern_parts, topic_parts):
                if pattern_part != "*" and pattern_part != topic_part:
                    return False
            
            return True
        
        return self.topic_pattern == topic

class EventBus:
    """
    Central event bus that manages event publishing and subscription.
    This is the nervous system of the Aetherion ecosystem.
    """
    
    def __init__(self, max_history: int = 1000):
        self.subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.max_history = max_history
        self.event_queue: Queue = Queue()
        self.running = False
        self.worker_thread = None
        
        # Statistics
        self.stats = {
            "events_published": 0,
            "events_delivered": 0,
            "subscriptions_active": 0
        }
        
    def start(self):
        """Start the event processing worker thread"""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._event_worker, daemon=True)
            self.worker_thread.start()
            logging.info("🚀 EventBus worker thread started")
    
    def stop(self):
        """Stop the event processing worker thread"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logging.info("🛑 EventBus stopped")
    
    def _event_worker(self):
        """Worker thread that processes events from the queue"""
        while self.running:
            try:
                # Get event with timeout
                event = self.event_queue.get(timeout=0.1)
                self._deliver_event(event)
                self.event_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logging.error(f"❌ Event worker error: {e}")
    
    def publish(self, topic: str, source: str, payload: Dict[str, Any], 
                priority: int = 0, ttl_seconds: Optional[int] = None,
                metadata: Dict[str, Any] = None) -> str:
        """Publish an event to the bus"""
        event = Event(
            id=str(uuid.uuid4()),
            topic=topic,
            source=source,
            payload=payload,
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata or {},
            priority=priority,
            ttl_seconds=ttl_seconds
        )
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        # Queue for processing
        self.event_queue.put(event)
        
        self.stats["events_published"] += 1
        
        logging.debug(f"📡 Event published: {topic} from {source}")
        return event.id
    
    def _deliver_event(self, event: Event):
        """Deliver an event to all matching subscribers"""
        if event.is_expired():
            logging.debug(f"⏰ Event {event.id} expired, skipping delivery")
            return
        
        delivered_count = 0
        
        # Find all matching subscriptions
        matching_subscriptions = []
        for topic_subs in self.subscriptions.values():
            for sub in topic_subs:
                if sub.active and sub.matches_topic(event.topic):
                    # Apply filter if present
                    if sub.filter_func is None or sub.filter_func(event):
                        matching_subscriptions.append(sub)
        
        # Sort by priority (higher priority events go first)
        matching_subscriptions.sort(key=lambda s: event.priority, reverse=True)
        
        # Deliver to each subscriber
        for subscription in matching_subscriptions:
            try:
                subscription.handler(event)
                delivered_count += 1
                logging.debug(f"📨 Event delivered to {subscription.subscriber}")
                
            except Exception as e:
                logging.error(f"❌ Event delivery failed for {subscription.subscriber}: {e}")
        
        self.stats["events_delivered"] += delivered_count
        
        if delivered_count == 0:
            logging.debug(f"👻 No subscribers for event topic: {event.topic}")
    
    def subscribe(self, topic_pattern: str, subscriber: str, 
                  handler: Callable[[Event], None],
                  filter_func: Optional[Callable[[Event], bool]] = None) -> str:
        """Subscribe to events matching a topic pattern"""
        subscription = Subscription(
            id=str(uuid.uuid4()),
            subscriber=subscriber,
            topic_pattern=topic_pattern,
            handler=handler,
            filter_func=filter_func
        )
        
        # Add to subscriptions
        self.subscriptions[topic_pattern].append(subscription)
        self.stats["subscriptions_active"] += 1
        
        logging.info(f"🔔 {subscriber} subscribed to {topic_pattern}")
        return subscription.id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe using subscription ID"""
        for topic_subs in self.subscriptions.values():
            for i, sub in enumerate(topic_subs):
                if sub.id == subscription_id:
                    topic_subs.pop(i)
                    self.stats["subscriptions_active"] -= 1
                    logging.info(f"🔕 Unsubscribed: {subscription_id}")
                    return True
        
        return False
    
    def get_history(self, topic_filter: Optional[str] = None, 
                   limit: Optional[int] = None) -> List[Event]:
        """Get event history, optionally filtered by topic"""
        events = self.event_history
        
        if topic_filter:
            events = [e for e in events if topic_filter in e.topic]
        
        if limit:
            events = events[-limit:]
        
        return events
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            **self.stats,
            "active_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
            "topics_with_subscribers": len(self.subscriptions),
            "events_in_history": len(self.event_history),
            "queue_size": self.event_queue.qsize()
        }

class EventPublisher:
    """
    Mixin class for agents that want to publish events.
    Provides a simple interface for event publishing.
    """
    
    def __init__(self, agent_name: str, event_bus: EventBus):
        self.agent_name = agent_name
        self.event_bus = event_bus
        
        # Subscribe to our own events for debugging
        self.event_bus.subscribe(
            f"{agent_name}.*",
            f"{agent_name}_debug",
            self._handle_own_event
        )
    
    def _handle_own_event(self, event: Event):
        """Handle events published by this agent (for debugging)"""
        logging.debug(f"🔍 {self.agent_name} published: {event.topic}")
    
    def publish_event(self, event_type: str, payload: Dict[str, Any],
                     priority: int = 0, ttl_seconds: Optional[int] = None) -> str:
        """Publish an event with this agent as the source"""
        topic = f"{self.agent_name}.{event_type}"
        return self.event_bus.publish(
            topic=topic,
            source=self.agent_name,
            payload=payload,
            priority=priority,
            ttl_seconds=ttl_seconds
        )
    
    def publish_task_started(self, task_type: str, task_data: Dict[str, Any]) -> str:
        """Convenience method for task started events"""
        return self.publish_event("task.started", {
            "task_type": task_type,
            "task_data": task_data,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def publish_task_completed(self, task_type: str, result: Dict[str, Any]) -> str:
        """Convenience method for task completed events"""
        return self.publish_event("task.completed", {
            "task_type": task_type,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def publish_task_failed(self, task_type: str, error: str) -> str:
        """Convenience method for task failed events"""
        return self.publish_event("task.failed", {
            "task_type": task_type,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })

class WorkflowEventHandler:
    """
    Specialized event handler for workflow orchestration.
    Listens for agent events and triggers workflow steps.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Subscribe to all task completion events
        self.event_bus.subscribe(
            "*.task.completed",
            "workflow_handler",
            self._handle_task_completion
        )
        
        # Subscribe to task failures
        self.event_bus.subscribe(
            "*.task.failed", 
            "workflow_handler",
            self._handle_task_failure
        )
    
    def _handle_task_completion(self, event: Event):
        """Handle task completion events for workflow progression"""
        agent_name = event.source
        task_type = event.payload.get("task_type")
        
        logging.info(f"🔄 Workflow handler: {agent_name} completed {task_type}")
        
        # Check if this completion triggers any workflows
        for workflow_id, workflow in self.active_workflows.items():
            if self._should_trigger_next_step(workflow, agent_name, task_type):
                self._trigger_next_workflow_step(workflow_id, workflow, event)
    
    def _handle_task_failure(self, event: Event):
        """Handle task failure events for workflow error handling"""
        agent_name = event.source
        task_type = event.payload.get("task_type")
        error = event.payload.get("error")
        
        logging.warning(f"⚠️ Workflow handler: {agent_name} failed {task_type}: {error}")
        
        # Mark any workflows using this task as failed
        for workflow_id, workflow in list(self.active_workflows.items()):
            if self._is_workflow_affected_by_failure(workflow, agent_name, task_type):
                self._handle_workflow_failure(workflow_id, workflow, event)
    
    def start_workflow(self, workflow_id: str, workflow_definition: Dict[str, Any]) -> str:
        """Start a new workflow"""
        self.active_workflows[workflow_id] = {
            "definition": workflow_definition,
            "status": "running",
            "current_step": 0,
            "started_at": datetime.utcnow().isoformat(),
            "completed_tasks": []
        }
        
        # Publish workflow started event
        self.event_bus.publish(
            "workflow.started",
            "workflow_handler",
            {
                "workflow_id": workflow_id,
                "definition": workflow_definition
            }
        )
        
        # Trigger first step
        self._trigger_next_workflow_step(workflow_id, self.active_workflows[workflow_id], None)
        
        return workflow_id
    
    def _should_trigger_next_step(self, workflow: Dict[str, Any], 
                                 agent_name: str, task_type: str) -> bool:
        """Check if a task completion should trigger the next workflow step"""
        definition = workflow["definition"]
        current_step = workflow["current_step"]
        
        if current_step >= len(definition.get("steps", [])):
            return False
        
        expected_step = definition["steps"][current_step]
        return (expected_step.get("agent") == agent_name and 
                expected_step.get("task_type") == task_type)
    
    def _trigger_next_workflow_step(self, workflow_id: str, workflow: Dict[str, Any], 
                                  trigger_event: Optional[Event]):
        """Trigger the next step in a workflow"""
        definition = workflow["definition"]
        current_step = workflow["current_step"]
        
        if current_step >= len(definition.get("steps", [])):
            # Workflow completed
            self._complete_workflow(workflow_id, workflow)
            return
        
        step = definition["steps"][current_step]
        agent_name = step.get("agent")
        task_type = step.get("task_type")
        task_params = step.get("params", {})
        
        # If previous step provided results, merge them
        if trigger_event and trigger_event.payload.get("result"):
            task_params.update(trigger_event.payload["result"])
        
        # Publish task request event
        self.event_bus.publish(
            f"{agent_name}.task.request",
            "workflow_handler",
            {
                "workflow_id": workflow_id,
                "step_index": current_step,
                "task_type": task_type,
                "params": task_params
            },
            priority=1  # Higher priority for workflow tasks
        )
        
        # Update workflow state
        workflow["current_step"] += 1
        
        logging.info(f"🎯 Triggered workflow step {current_step}: {agent_name}.{task_type}")
    
    def _complete_workflow(self, workflow_id: str, workflow: Dict[str, Any]):
        """Complete a workflow"""
        workflow["status"] = "completed"
        workflow["completed_at"] = datetime.utcnow().isoformat()
        
        # Publish workflow completed event
        self.event_bus.publish(
            "workflow.completed",
            "workflow_handler",
            {
                "workflow_id": workflow_id,
                "workflow": workflow
            }
        )
        
        # Remove from active workflows
        del self.active_workflows[workflow_id]
        
        logging.info(f"✅ Workflow completed: {workflow_id}")
    
    def _is_workflow_affected_by_failure(self, workflow: Dict[str, Any], 
                                       agent_name: str, task_type: str) -> bool:
        """Check if a task failure affects this workflow"""
        definition = workflow["definition"]
        current_step = workflow["current_step"]
        
        if current_step >= len(definition.get("steps", [])):
            return False
        
        expected_step = definition["steps"][current_step - 1]  # Previous step that should have completed
        return (expected_step.get("agent") == agent_name and 
                expected_step.get("task_type") == task_type)
    
    def _handle_workflow_failure(self, workflow_id: str, workflow: Dict[str, Any], 
                                error_event: Event):
        """Handle workflow failure"""
        workflow["status"] = "failed"
        workflow["failed_at"] = datetime.utcnow().isoformat()
        workflow["failure_reason"] = error_event.payload.get("error", "Unknown error")
        
        # Publish workflow failed event
        self.event_bus.publish(
            "workflow.failed",
            "workflow_handler",
            {
                "workflow_id": workflow_id,
                "workflow": workflow,
                "error_event": asdict(error_event)
            }
        )
        
        # Remove from active workflows
        del self.active_workflows[workflow_id]
        
        logging.error(f"❌ Workflow failed: {workflow_id}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow"""
        return self.active_workflows.get(workflow_id)
    
    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        return [
            {"workflow_id": wid, **workflow}
            for wid, workflow in self.active_workflows.items()
        ]

# Global event bus instance
_global_event_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
        _global_event_bus.start()
    return _global_event_bus

def shutdown_event_bus():
    """Shutdown the global event bus"""
    global _global_event_bus
    if _global_event_bus:
        _global_event_bus.stop()
        _global_event_bus = None
