# Resource Governance Manager
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import yaml
import asyncio
from prometheus_client import Gauge, Counter, Histogram
import logging

logger = logging.getLogger(__name__)

# Metrics
resource_usage_gauge = Gauge('resource_usage_ratio', 'Resource usage ratio', ['service', 'resource_type'])
cost_gauge = Gauge('cost_usd', 'Cost in USD', ['service', 'cost_type'])
quota_usage_gauge = Gauge('quota_usage_ratio', 'Quota usage ratio', ['tenant', 'quota_type'])
sla_compliance_gauge = Gauge('sla_compliance_ratio', 'SLA compliance ratio', ['service', 'sla_type'])
budget_alert_counter = Counter('budget_alerts_total', 'Budget alerts triggered', ['severity', 'category'])

class ResourceUsage(BaseModel):
    """Resource usage metrics"""
    service: str
    cpu_usage_cores: float
    memory_usage_gb: float
    storage_usage_gb: float
    network_io_mbps: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CostMetrics(BaseModel):
    """Cost tracking metrics"""
    service: str
    compute_cost_usd: float
    storage_cost_usd: float
    network_cost_usd: float
    llm_cost_usd: float
    total_cost_usd: float
    period_start: datetime
    period_end: datetime

class QuotaUsage(BaseModel):
    """Quota usage tracking"""
    tenant_id: str
    quota_type: str
    used: float
    limit: float
    usage_ratio: float = Field(computed=True)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.usage_ratio = self.used / self.limit if self.limit > 0 else 0

class ResourceGovernanceManager:
    """Central resource governance manager"""
    
    def __init__(self, config_path: str = "config/resource_governance.yaml"):
        self.config = self._load_config(config_path)
        self.resource_usage_history: List[ResourceUsage] = []
        self.cost_history: List[CostMetrics] = []
        self.quota_usage: Dict[str, List[QuotaUsage]] = {}
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load resource governance configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def collect_resource_metrics(self) -> List[ResourceUsage]:
        """Collect current resource usage metrics"""
        # This would integrate with your existing Prometheus metrics
        # For now, returning mock data structure
        services = ['api', 'doc-writer', 'frontend-dev', 'backend-dev', 'qa-tester', 'compliance-checker']
        metrics = []
        
        for service in services:
            # In real implementation, query Prometheus for actual metrics
            usage = ResourceUsage(
                service=service,
                cpu_usage_cores=0.0,  # Query from Prometheus
                memory_usage_gb=0.0,  # Query from Prometheus
                storage_usage_gb=0.0, # Query from Prometheus
                network_io_mbps=0.0   # Query from Prometheus
            )
            metrics.append(usage)
            
            # Update Prometheus metrics
            resource_usage_gauge.labels(service=service, resource_type='cpu').set(usage.cpu_usage_cores)
            resource_usage_gauge.labels(service=service, resource_type='memory').set(usage.memory_usage_gb)
            resource_usage_gauge.labels(service=service, resource_type='storage').set(usage.storage_usage_gb)
        
        self.resource_usage_history.extend(metrics)
        return metrics
    
    async def calculate_costs(self, period_hours: int = 24) -> List[CostMetrics]:
        """Calculate costs for the specified period"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=period_hours)
        
        # Cost calculation logic based on resource usage
        # This would integrate with cloud provider billing APIs
        services = ['api', 'doc-writer', 'frontend-dev', 'backend-dev', 'qa-tester', 'compliance-checker']
        cost_metrics = []
        
        for service in services:
            # Calculate costs based on usage and pricing models
            cost = CostMetrics(
                service=service,
                compute_cost_usd=0.0,  # Calculate from CPU/memory usage
                storage_cost_usd=0.0,  # Calculate from storage usage
                network_cost_usd=0.0,  # Calculate from network I/O
                llm_cost_usd=0.0,      # Calculate from token usage
                total_cost_usd=0.0,    # Sum of all costs
                period_start=start_time,
                period_end=end_time
            )
            cost.total_cost_usd = (
                cost.compute_cost_usd + cost.storage_cost_usd + 
                cost.network_cost_usd + cost.llm_cost_usd
            )
            cost_metrics.append(cost)
            
            # Update cost metrics
            cost_gauge.labels(service=service, cost_type='compute').set(cost.compute_cost_usd)
            cost_gauge.labels(service=service, cost_type='storage').set(cost.storage_cost_usd)
            cost_gauge.labels(service=service, cost_type='network').set(cost.network_cost_usd)
            cost_gauge.labels(service=service, cost_type='llm').set(cost.llm_cost_usd)
            cost_gauge.labels(service=service, cost_type='total').set(cost.total_cost_usd)
        
        self.cost_history.extend(cost_metrics)
        return cost_metrics
    
    async def check_quota_compliance(self, tenant_id: str) -> List[QuotaUsage]:
        """Check quota usage for a tenant"""
        tenant_quotas = self.config['quotas']['per_tenant']
        quota_usage = []
        
        for quota_type, limit in tenant_quotas.items():
            # Get current usage from metrics/database
            current_usage = await self._get_current_usage(tenant_id, quota_type)
            
            usage = QuotaUsage(
                tenant_id=tenant_id,
                quota_type=quota_type,
                used=current_usage,
                limit=limit
            )
            quota_usage.append(usage)
            
            # Update quota metrics
            quota_usage_gauge.labels(tenant=tenant_id, quota_type=quota_type).set(usage.usage_ratio)
            
            # Check for quota violations
            if usage.usage_ratio > 0.9:  # 90% threshold
                logger.warning(f"Quota warning for {tenant_id}: {quota_type} at {usage.usage_ratio:.1%}")
            elif usage.usage_ratio > 1.0:  # Over quota
                logger.error(f"Quota exceeded for {tenant_id}: {quota_type} at {usage.usage_ratio:.1%}")
        
        self.quota_usage[tenant_id] = quota_usage
        return quota_usage
    
    async def _get_current_usage(self, tenant_id: str, quota_type: str) -> float:
        """Get current usage for a specific quota type"""
        # This would query your database/metrics for actual usage
        # Placeholder implementation
        return 0.0
    
    async def check_budget_compliance(self) -> Dict[str, float]:
        """Check budget compliance and trigger alerts"""
        budget_config = self.config['policies']['cost']
        total_budget = budget_config['total_budget_usd']
        alert_thresholds = budget_config['budget_alert_thresholds']
        
        # Calculate current month spend
        current_spend = await self._calculate_monthly_spend()
        spend_ratio = current_spend / total_budget
        
        # Check alert thresholds
        for severity, threshold in alert_thresholds.items():
            if spend_ratio >= threshold / 100:
                budget_alert_counter.labels(severity=severity, category='total').inc()
                await self._send_budget_alert(severity, current_spend, total_budget)
        
        return {
            'current_spend': current_spend,
            'total_budget': total_budget,
            'spend_ratio': spend_ratio,
            'remaining_budget': total_budget - current_spend
        }
    
    async def _calculate_monthly_spend(self) -> float:
        """Calculate current month spend"""
        # Query cost history for current month
        # Placeholder implementation
        return 0.0
    
    async def _send_budget_alert(self, severity: str, current_spend: float, total_budget: float):
        """Send budget alert notification"""
        message = f"Budget Alert ({severity}): Current spend ${current_spend:.2f} of ${total_budget:.2f}"
        logger.warning(message)
        # Implement actual alerting (Slack, email, PagerDuty)
    
    async def enforce_resource_limits(self, service: str, resource_type: str, current_usage: float) -> bool:
        """Enforce resource limits for a service"""
        limits = self.config['policies']['compute']
        
        if resource_type == 'cpu':
            limit = float(limits['cpu_limits'][service].rstrip('m')) / 1000  # Convert to cores
        elif resource_type == 'memory':
            limit = self._parse_memory_limit(limits['memory_limits'][service])
        else:
            return True  # Unknown resource type, allow
        
        if current_usage > limit:
            logger.error(f"Resource limit exceeded for {service}: {resource_type} usage {current_usage} > limit {limit}")
            # Implement enforcement action (scale down, throttle, etc.)
            return False
        
        return True
    
    def _parse_memory_limit(self, memory_str: str) -> float:
        """Parse memory limit string to GB"""
        if memory_str.endswith('Gi'):
            return float(memory_str[:-2])
        elif memory_str.endswith('Mi'):
            return float(memory_str[:-2]) / 1024
        else:
            return float(memory_str)
    
    async def generate_governance_report(self) -> Dict[str, Any]:
        """Generate comprehensive governance report"""
        resource_metrics = await self.collect_resource_metrics()
        cost_metrics = await self.calculate_costs()
        budget_status = await self.check_budget_compliance()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'resource_utilization': {
                'services': [metric.dict() for metric in resource_metrics]
            },
            'cost_analysis': {
                'services': [metric.dict() for metric in cost_metrics],
                'budget_status': budget_status
            },
            'sla_compliance': await self._check_sla_compliance(),
            'recommendations': await self._generate_recommendations()
        }
    
    async def _check_sla_compliance(self) -> Dict[str, Any]:
        """Check SLA compliance"""
        # Query metrics for SLA compliance
        # Placeholder implementation
        return {
            'availability': {'api': 99.95, 'agents': 99.8},
            'performance': {'api_latency_p95': 150, 'throughput': 1200}
        }
    
    async def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Analyze resource usage patterns and generate recommendations
        # This would use ML/heuristics to suggest optimizations
        
        return recommendations