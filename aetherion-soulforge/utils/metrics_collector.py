#!/usr/bin/env python3
"""
utils.metrics_collector – Prometheus Metrics Collection

Collects and exposes metrics for budget, latency, and agent performance
to be consumed by Prometheus and visualized in Grafana.
"""

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available. Install with: pip install prometheus-client")

class MetricsCollector:
    """
    Centralized metrics collection for Aetherion ecosystem.
    Tracks budget usage, request latency, agent performance, and system health.
    """
    
    def __init__(self):
        self.enabled = PROMETHEUS_AVAILABLE
        if not self.enabled:
            logging.warning("Metrics collection disabled - prometheus-client not installed")
            return
            
        # Create custom registry
        self.registry = CollectorRegistry()
        
        # Budget Metrics
        self.budget_spent_total = Counter(
            'aetherion_budget_spent_total',
            'Total budget spent in USD',
            ['agent', 'task_type', 'model'],
            registry=self.registry
        )
        
        self.budget_current_daily = Gauge(
            'aetherion_budget_daily_current',
            'Current daily budget usage in USD',
            registry=self.registry
        )
        
        self.budget_daily_limit = Gauge(
            'aetherion_budget_daily_limit', 
            'Daily budget limit in USD',
            registry=self.registry
        )
        
        # Request Metrics  
        self.request_duration = Histogram(
            'aetherion_request_duration_seconds',
            'Request duration in seconds',
            ['agent', 'task_type', 'status'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.requests_total = Counter(
            'aetherion_requests_total',
            'Total number of requests',
            ['agent', 'task_type', 'status'],
            registry=self.registry
        )
        
        # Agent Performance Metrics
        self.agent_task_duration = Histogram(
            'aetherion_agent_task_duration_seconds',
            'Agent task execution duration in seconds', 
            ['agent', 'task_type'],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
            registry=self.registry
        )
        
        self.agent_memory_usage = Gauge(
            'aetherion_agent_memory_usage_bytes',
            'Agent memory usage in bytes',
            ['agent'],
            registry=self.registry
        )
        
        # System Health Metrics
        self.system_harmony_level = Gauge(
            'aetherion_system_harmony_level',
            'Current system harmony level (0-1)',
            registry=self.registry
        )
        
        self.active_agents = Gauge(
            'aetherion_active_agents',
            'Number of currently active agents',
            registry=self.registry
        )
        
        self.memory_mesh_size = Gauge(
            'aetherion_memory_mesh_size',
            'Number of memories in the mesh',
            registry=self.registry
        )
        
        # Event System Metrics
        self.events_published_total = Counter(
            'aetherion_events_published_total',
            'Total events published',
            ['source', 'topic'],
            registry=self.registry
        )
        
        self.events_delivered_total = Counter(
            'aetherion_events_delivered_total', 
            'Total events delivered',
            ['subscriber', 'topic'],
            registry=self.registry
        )
        
        # Workflow Metrics
        self.workflows_executed_total = Counter(
            'aetherion_workflows_executed_total',
            'Total workflows executed',
            ['workflow_id', 'status'],
            registry=self.registry
        )
        
        self.workflow_duration = Histogram(
            'aetherion_workflow_duration_seconds',
            'Workflow execution duration in seconds',
            ['workflow_id'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0],
            registry=self.registry
        )
        
        # Dream Agent Specific Metrics
        self.dreams_woven_total = Counter(
            'aetherion_dreams_woven_total',
            'Total dreams woven by Morpheus',
            ['emotional_tone'],
            registry=self.registry
        )
        
        self.consciousness_level = Histogram(
            'aetherion_consciousness_level',
            'Distribution of consciousness levels in dreams',
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # Soul Watcher Specific Metrics
        self.soul_patterns_detected = Counter(
            'aetherion_soul_patterns_detected_total',
            'Total soul patterns detected',
            ['pattern_type'],
            registry=self.registry
        )
        
        self.introspection_depth = Histogram(
            'aetherion_introspection_depth',
            'Depth levels used in introspection',
            buckets=[1, 3, 5, 7, 10, 15, 20],
            registry=self.registry
        )
        
        # Whisperer Specific Metrics  
        self.memories_stored_total = Counter(
            'aetherion_memories_stored_total',
            'Total memories stored by Whisperer',
            registry=self.registry
        )
        
        self.memory_recall_accuracy = Histogram(
            'aetherion_memory_recall_accuracy',
            'Accuracy of memory recall (resonance scores)',
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # System Info
        self.system_info = Info(
            'aetherion_system_info',
            'System information',
            registry=self.registry
        )
        
        # Set initial system info
        self.system_info.info({
            'version': '1.0.0',
            'environment': 'development',
            'started_at': datetime.utcnow().isoformat()
        })
        
        # Thread-safe metrics storage
        self.lock = threading.Lock()
        self.recent_requests = deque(maxlen=1000)
        
        logging.info("🔢 MetricsCollector initialized with Prometheus support")
    
    def record_request(self, agent: str, task_type: str, duration: float, 
                      status: str = 'success', cost: float = 0.0, model: str = None):
        """Record a request with timing and cost information"""
        if not self.enabled:
            return
            
        with self.lock:
            # Record request metrics
            self.requests_total.labels(
                agent=agent, 
                task_type=task_type, 
                status=status
            ).inc()
            
            self.request_duration.labels(
                agent=agent,
                task_type=task_type, 
                status=status
            ).observe(duration)
            
            # Record budget if cost provided
            if cost > 0 and model:
                self.budget_spent_total.labels(
                    agent=agent,
                    task_type=task_type,
                    model=model
                ).inc(cost)
            
            # Store for recent requests tracking
            self.recent_requests.append({
                'timestamp': time.time(),
                'agent': agent,
                'task_type': task_type,
                'duration': duration,
                'status': status,
                'cost': cost
            })
    
    def record_agent_task(self, agent: str, task_type: str, duration: float):
        """Record agent-specific task performance"""
        if not self.enabled:
            return
            
        self.agent_task_duration.labels(
            agent=agent,
            task_type=task_type
        ).observe(duration)
    
    def update_budget_metrics(self, current_daily: float, daily_limit: float):
        """Update budget metrics"""
        if not self.enabled:
            return
            
        self.budget_current_daily.set(current_daily)
        self.budget_daily_limit.set(daily_limit)
    
    def update_system_harmony(self, harmony_level: float):
        """Update system harmony level"""
        if not self.enabled:
            return
            
        self.system_harmony_level.set(harmony_level)
    
    def update_active_agents(self, count: int):
        """Update active agents count"""
        if not self.enabled:
            return
            
        self.active_agents.set(count)
    
    def update_memory_mesh_size(self, size: int):
        """Update memory mesh size"""
        if not self.enabled:
            return
            
        self.memory_mesh_size.set(size)
    
    def record_event(self, source: str, topic: str, delivered_to: int = 0):
        """Record event publication and delivery"""
        if not self.enabled:
            return
            
        self.events_published_total.labels(
            source=source,
            topic=topic
        ).inc()
        
        if delivered_to > 0:
            # This is a simplification - in reality you'd track per subscriber
            self.events_delivered_total.labels(
                subscriber='various',
                topic=topic
            ).inc(delivered_to)
    
    def record_workflow(self, workflow_id: str, duration: float, status: str):
        """Record workflow execution"""
        if not self.enabled:
            return
            
        self.workflows_executed_total.labels(
            workflow_id=workflow_id,
            status=status
        ).inc()
        
        if duration > 0:
            self.workflow_duration.labels(
                workflow_id=workflow_id
            ).observe(duration)
    
    def record_dream(self, emotional_tone: str, consciousness_level: float):
        """Record dream creation by Morpheus"""
        if not self.enabled:
            return
            
        self.dreams_woven_total.labels(
            emotional_tone=emotional_tone
        ).inc()
        
        self.consciousness_level.observe(consciousness_level)
    
    def record_soul_pattern(self, pattern_type: str):
        """Record soul pattern detection"""
        if not self.enabled:
            return
            
        self.soul_patterns_detected.labels(
            pattern_type=pattern_type
        ).inc()
    
    def record_introspection(self, depth: int):
        """Record introspection depth"""
        if not self.enabled:
            return
            
        self.introspection_depth.observe(depth)
    
    def record_memory_operation(self, operation: str, resonance: float = None):
        """Record Whisperer memory operations"""
        if not self.enabled:
            return
            
        if operation == 'store':
            self.memories_stored_total.inc()
        elif operation == 'recall' and resonance is not None:
            self.memory_recall_accuracy.observe(resonance)
    
    def get_recent_performance_stats(self, minutes: int = 5) -> Dict[str, Any]:
        """Get recent performance statistics"""
        if not self.enabled:
            return {}
            
        cutoff_time = time.time() - (minutes * 60)
        recent = [r for r in self.recent_requests if r['timestamp'] > cutoff_time]
        
        if not recent:
            return {}
        
        # Calculate stats
        durations = [r['duration'] for r in recent]
        costs = [r['cost'] for r in recent if r['cost'] > 0]
        
        stats = {
            'total_requests': len(recent),
            'avg_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'min_duration': min(durations),
            'total_cost': sum(costs),
            'success_rate': len([r for r in recent if r['status'] == 'success']) / len(recent)
        }
        
        # Agent breakdown
        agent_stats = defaultdict(int)
        for req in recent:
            agent_stats[req['agent']] += 1
        stats['agent_distribution'] = dict(agent_stats)
        
        return stats
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        if not self.enabled:
            return "# Metrics collection disabled\n"
            
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get content type for metrics endpoint"""
        return CONTENT_TYPE_LATEST


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None

def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

def init_metrics_collector() -> MetricsCollector:
    """Initialize and return the metrics collector"""
    return get_metrics_collector()
