# Path A: Enterprise-Grade Operations Implementation

This document outlines the implementation of enterprise-grade operational features for the Codessa Dynamic LLM Router, building on the existing router architecture.

---

## 0) Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Enterprise Layer                         │
├─────────────────────────────────────────────────────────────┤
│ Multi-Tenant Router │ SLA Manager │ Cost Attribution │ DR   │
├─────────────────────────────────────────────────────────────┤
│                  Existing Router Core                      │
└─────────────────────────────────────────────────────────────┘
```

**Key Components:**
- **Tenant Router**: Per-organization routing policies and resource isolation
- **SLA Manager**: Performance guarantees with automatic failover
- **Cost Attribution**: Granular usage tracking and billing integration
- **Disaster Recovery**: Multi-region deployment with automatic failover
- **Advanced Observability**: User journey mapping and predictive analytics

---

## 1) Multi-Tenant Routing Architecture

### File Structure
```
/enterprise/
  tenant_router.py         # Per-tenant routing logic
  tenant_registry.py       # Tenant configuration management
  resource_isolation.py    # Resource limits and quotas
  billing_integration.py   # Usage tracking and billing
/ops/
  tenant_policies/         # Per-tenant OPA policies
  deployment/
    multi-region.yml       # K8s multi-region deployment
```

### Tenant Router Implementation

**`/enterprise/tenant_router.py`**
```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import asyncio
from datetime import datetime, timedelta

class TierLevel(Enum):
    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

@dataclass
class TenantConfig:
    tenant_id: str
    tier: TierLevel
    allowed_models: List[str]
    max_requests_per_minute: int
    max_cost_per_day: float
    sla_latency_ms: Optional[int]
    priority_queue: bool = False
    custom_routing_rules: Dict = None
    
class TenantRouter:
    def __init__(self, tenant_registry):
        self.registry = tenant_registry
        self.usage_tracker = UsageTracker()
        
    async def route_for_tenant(self, tenant_id: str, request, base_decision):
        """Override base routing with tenant-specific rules"""
        config = await self.registry.get_config(tenant_id)
        
        # Check rate limits
        if not await self._check_rate_limit(tenant_id, config):
            raise RateLimitExceeded(f"Rate limit exceeded for tenant {tenant_id}")
            
        # Check daily budget
        if not await self._check_budget(tenant_id, config, base_decision):
            # Fallback to cheaper model or deny
            return await self._budget_fallback(base_decision, config)
            
        # Apply tier-specific routing
        if config.tier == TierLevel.ENTERPRISE:
            return await self._enterprise_routing(request, base_decision, config)
        elif config.tier == TierLevel.PROFESSIONAL:
            return await self._professional_routing(request, base_decision, config)
        else:
            return await self._free_tier_routing(request, base_decision, config)
    
    async def _enterprise_routing(self, request, decision, config):
        """Enterprise tier gets priority models and custom rules"""
        if config.custom_routing_rules:
            custom_decision = await self._apply_custom_rules(request, config.custom_routing_rules)
            if custom_decision:
                return custom_decision
                
        # Prioritize strongest models
        if decision["model"] in ["mistral-small", "llama3.1"]:
            # Upgrade to premium model for enterprise
            return {
                **decision,
                "model": "gpt-5",
                "reason": f"{decision['reason']}-enterprise-upgrade",
                "tenant_tier": "enterprise"
            }
        return {**decision, "tenant_tier": "enterprise"}
        
    async def _professional_routing(self, request, decision, config):
        """Professional tier gets balanced cost/quality"""
        # Allow upgrades for complex tasks
        complexity_score = self._calculate_complexity(request)
        if complexity_score > 0.7 and decision["model"] == "mistral-small":
            return {
                **decision,
                "model": "claude-3-7",
                "reason": f"{decision['reason']}-pro-upgrade",
                "tenant_tier": "professional"
            }
        return {**decision, "tenant_tier": "professional"}
        
    async def _free_tier_routing(self, request, decision, config):
        """Free tier limited to cheap models"""
        if decision["model"] not in config.allowed_models:
            return {
                **decision,
                "model": "mistral-small",
                "reason": "free-tier-downgrade",
                "tenant_tier": "free"
            }
        return {**decision, "tenant_tier": "free"}

class UsageTracker:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def track_request(self, tenant_id: str, cost: float, latency_ms: int, model: str):
        """Track usage for billing and analytics"""
        now = datetime.utcnow()
        day_key = f"usage:{tenant_id}:{now.strftime('%Y-%m-%d')}"
        minute_key = f"rate:{tenant_id}:{now.strftime('%Y-%m-%d:%H:%M')}"
        
        pipe = self.redis.pipeline()
        # Daily usage
        pipe.hincrbyfloat(day_key, "cost", cost)
        pipe.hincrby(day_key, "requests", 1)
        pipe.hincrby(day_key, f"model:{model}", 1)
        pipe.expire(day_key, 86400 * 32)  # Keep 32 days
        
        # Rate limiting
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        
        await pipe.execute()
```

### Tenant Registry

**`/enterprise/tenant_registry.py`**
```python
import yaml
import aiofiles
from typing import Dict
import os

class TenantRegistry:
    def __init__(self, config_path: str = "/config/tenants.yaml"):
        self.config_path = config_path
        self.configs: Dict[str, TenantConfig] = {}
        
    async def load_configs(self):
        """Load tenant configurations from YAML"""
        async with aiofiles.open(self.config_path) as f:
            content = await f.read()
            data = yaml.safe_load(content)
            
        for tenant_data in data.get("tenants", []):
            config = TenantConfig(**tenant_data)
            self.configs[config.tenant_id] = config
            
    async def get_config(self, tenant_id: str) -> TenantConfig:
        if not self.configs:
            await self.load_configs()
            
        return self.configs.get(tenant_id, self._default_config(tenant_id))
        
    def _default_config(self, tenant_id: str) -> TenantConfig:
        """Default free tier configuration"""
        return TenantConfig(
            tenant_id=tenant_id,
            tier=TierLevel.FREE,
            allowed_models=["mistral-small", "llama3.1"],
            max_requests_per_minute=10,
            max_cost_per_day=1.0,
            sla_latency_ms=None
        )
```

---

## 2) SLA Management System

**`/enterprise/sla_manager.py`**
```python
import asyncio
import time
from enum import Enum
from typing import Dict, List
import logging

class SLAViolationType(Enum):
    LATENCY = "latency"
    AVAILABILITY = "availability"
    QUALITY = "quality"

class SLAManager:
    def __init__(self, tenant_registry, alert_manager):
        self.registry = tenant_registry
        self.alerts = alert_manager
        self.violation_counters = {}
        
    async def check_sla_requirements(self, tenant_id: str, request_start: float):
        """Check if request meets SLA requirements"""
        config = await self.registry.get_config(tenant_id)
        
        if not config.sla_latency_ms:
            return True  # No SLA defined
            
        elapsed_ms = (time.time() - request_start) * 1000
        
        if elapsed_ms > config.sla_latency_ms:
            await self._record_violation(tenant_id, SLAViolationType.LATENCY, elapsed_ms)
            return False
            
        return True
        
    async def get_routing_priority(self, tenant_id: str) -> int:
        """Get routing priority based on SLA tier"""
        config = await self.registry.get_config(tenant_id)
        
        if config.sla_latency_ms and config.sla_latency_ms <= 1000:
            return 1  # High priority
        elif config.sla_latency_ms and config.sla_latency_ms <= 3000:
            return 2  # Medium priority
        else:
            return 3  # Low priority
            
    async def _record_violation(self, tenant_id: str, violation_type: SLAViolationType, value: float):
        """Record SLA violation and trigger alerts if needed"""
        key = f"{tenant_id}:{violation_type.value}"
        
        if key not in self.violation_counters:
            self.violation_counters[key] = []
            
        self.violation_counters[key].append({
            "timestamp": time.time(),
            "value": value
        })
        
        # Clean old violations (last hour)
        hour_ago = time.time() - 3600
        self.violation_counters[key] = [
            v for v in self.violation_counters[key] 
            if v["timestamp"] > hour_ago
        ]
        
        # Alert if more than 5 violations in the last hour
        if len(self.violation_counters[key]) >= 5:
            await self.alerts.send_sla_alert(tenant_id, violation_type, len(self.violation_counters[key]))

class PriorityQueue:
    """Priority-based request queue for SLA management"""
    def __init__(self):
        self.queues = {1: asyncio.Queue(), 2: asyncio.Queue(), 3: asyncio.Queue()}
        
    async def put(self, item, priority: int = 3):
        await self.queues[min(priority, 3)].put(item)
        
    async def get(self):
        """Get highest priority item available"""
        for priority in [1, 2, 3]:
            if not self.queues[priority].empty():
                return await self.queues[priority].get()
        
        # If all queues empty, wait for any item
        done, pending = await asyncio.wait(
            [q.get() for q in self.queues.values()],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            
        return done.pop().result()
```

---

## 3) Cost Attribution & Billing Integration

**`/enterprise/billing_integration.py`**
```python
import asyncio
from decimal import Decimal
from typing import Dict, List
from datetime import datetime, timedelta
import json

class CostAttributor:
    def __init__(self, usage_tracker, billing_client):
        self.usage_tracker = usage_tracker
        self.billing_client = billing_client
        
    async def attribute_cost(self, tenant_id: str, request_context: Dict, response: Dict):
        """Attribute cost to specific tenant/user/project"""
        cost_breakdown = {
            "tenant_id": tenant_id,
            "user_id": request_context.get("user_id"),
            "project_id": request_context.get("project_id"),
            "session_id": request_context.get("session_id"),
            "model": response.get("route", {}).get("model"),
            "provider_cost": response.get("cost", {}).get("estimated_usd", 0),
            "markup_cost": self._calculate_markup(tenant_id, response),
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": response.get("trace_id"),
            "tokens_prompt": response.get("usage", {}).get("prompt_tokens", 0),
            "tokens_completion": response.get("usage", {}).get("completion_tokens", 0),
            "cached": response.get("route", {}).get("decision") == "cache"
        }
        
        # Store for billing
        await self.usage_tracker.record_cost_event(cost_breakdown)
        
        # Real-time billing update for enterprise customers
        config = await self.registry.get_config(tenant_id)
        if config.tier == TierLevel.ENTERPRISE:
            await self.billing_client.update_usage(tenant_id, cost_breakdown)
            
    def _calculate_markup(self, tenant_id: str, response: Dict) -> float:
        """Calculate markup based on tenant tier and model"""
        base_cost = response.get("cost", {}).get("estimated_usd", 0)
        model = response.get("route", {}).get("model")
        
        # Markup rates by tier
        markup_rates = {
            TierLevel.FREE: 0.0,  # No markup for free tier (limited usage)
            TierLevel.PROFESSIONAL: 0.2,  # 20% markup
            TierLevel.ENTERPRISE: 0.15   # 15% markup (volume discount)
        }
        
        # Premium model surcharge
        premium_models = ["gpt-5", "claude-3-7"]
        surcharge = 0.1 if model in premium_models else 0.0
        
        config = self.registry.get_config_sync(tenant_id)
        markup_rate = markup_rates.get(config.tier, 0.2)
        
        return base_cost * (markup_rate + surcharge)

class BillingClient:
    """Integration with external billing system (Stripe, etc.)"""
    def __init__(self, billing_api_url: str, api_key: str):
        self.api_url = billing_api_url
        self.api_key = api_key
        
    async def update_usage(self, tenant_id: str, cost_event: Dict):
        """Update usage-based billing in real-time"""
        payload = {
            "customer_id": tenant_id,
            "usage_record": {
                "quantity": cost_event["provider_cost"] + cost_event["markup_cost"],
                "timestamp": cost_event["timestamp"],
                "metadata": {
                    "model": cost_event["model"],
                    "trace_id": cost_event["trace_id"],
                    "tokens_total": cost_event["tokens_prompt"] + cost_event["tokens_completion"]
                }
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/usage-records",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                if not response.ok:
                    logging.error(f"Billing update failed: {await response.text()}")

class UsageDashboard:
    """Generate usage reports and dashboards for tenants"""
    def __init__(self, usage_tracker):
        self.usage_tracker = usage_tracker
        
    async def generate_tenant_report(self, tenant_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Generate detailed usage report for tenant"""
        usage_data = await self.usage_tracker.get_usage_range(tenant_id, start_date, end_date)
        
        return {
            "tenant_id": tenant_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_requests": sum(day["requests"] for day in usage_data),
                "total_cost": sum(day["cost"] for day in usage_data),
                "avg_cost_per_request": self._avg_cost_per_request(usage_data),
                "top_models": self._top_models(usage_data),
                "cache_hit_rate": self._cache_hit_rate(usage_data)
            },
            "daily_breakdown": usage_data,
            "cost_optimization_suggestions": self._generate_suggestions(usage_data)
        }
        
    def _generate_suggestions(self, usage_data: List[Dict]) -> List[str]:
        """Generate cost optimization suggestions"""
        suggestions = []
        
        # Analyze model usage patterns
        model_costs = {}
        for day in usage_data:
            for model, count in day.get("models", {}).items():
                if model not in model_costs:
                    model_costs[model] = {"count": 0, "cost": 0}
                model_costs[model]["count"] += count
                
        # Suggest cheaper alternatives for high-usage expensive models
        if model_costs.get("gpt-5", {}).get("count", 0) > 100:
            suggestions.append("Consider using claude-3-7 for code tasks - similar quality at 20% lower cost")
            
        if model_costs.get("claude-3-7", {}).get("count", 0) > 200:
            suggestions.append("Enable semantic caching to reduce duplicate requests by ~30%")
            
        return suggestions
```

---

## 4) Disaster Recovery & Multi-Region Deployment

**`/ops/deployment/multi-region.yml`**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: codessa-router
---
# Primary Region Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: router-primary
  namespace: codessa-router
  labels:
    app: codessa-router
    region: primary
spec:
  replicas: 3
  selector:
    matchLabels:
      app: codessa-router
      region: primary
  template:
    metadata:
      labels:
        app: codessa-router
        region: primary
    spec:
      containers:
      - name: router
        image: codessa/router:latest
        env:
        - name: REGION
          value: "primary"
        - name: FAILOVER_REGIONS
          value: "secondary,tertiary"
        - name: REDIS_URL
          value: "redis://redis-primary:6379"
        - name: PG_DSN
          value: "postgresql://postgres-primary:5432/router"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
---
# Service with cross-region load balancing
apiVersion: v1
kind: Service
metadata:
  name: router-global-lb
  namespace: codessa-router
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "false"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: codessa-router
---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: router-hpa
  namespace: codessa-router
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: router-primary
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Disaster Recovery Manager**

**`/enterprise/disaster_recovery.py`**
```python
import asyncio
import aiohttp
import logging
from typing import List, Dict
from enum import Enum

class RegionStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"

class DisasterRecoveryManager:
    def __init__(self, regions: List[Dict]):
        self.regions = regions  # [{"name": "primary", "url": "...", "priority": 1}]
        self.region_status = {}
        self.active_region = None
        
    async def start_health_monitoring(self):
        """Start continuous health monitoring of all regions"""
        while True:
            await self._check_all_regions()
            await self._update_active_region()
            await asyncio.sleep(10)  # Check every 10 seconds
            
    async def _check_all_regions(self):
        """Health check all regions in parallel"""
        tasks = []
        for region in self.regions:
            task = asyncio.create_task(self._check_region_health(region))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for region, result in zip(self.regions, results):
            if isinstance(result, Exception):
                self.region_status[region["name"]] = RegionStatus.FAILED
                logging.error(f"Region {region['name']} health check failed: {result}")
            else:
                self.region_status[region["name"]] = result
                
    async def _check_region_health(self, region: Dict) -> RegionStatus:
        """Check health of a single region"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{region['url']}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check various health metrics
                        if data.get("database_ok") and data.get("cache_ok") and data.get("avg_latency_ms", 0) < 2000:
                            return RegionStatus.HEALTHY
                        else:
                            return RegionStatus.DEGRADED
                    else:
                        return RegionStatus.FAILED
                        
        except Exception as e:
            logging.warning(f"Region {region['name']} health check exception: {e}")
            return RegionStatus.FAILED
            
    async def _update_active_region(self):
        """Update active region based on health and priority"""
        # Sort regions by priority (lower number = higher priority)
        sorted_regions = sorted(self.regions, key=lambda r: r["priority"])
        
        for region in sorted_regions:
            status = self.region_status.get(region["name"], RegionStatus.FAILED)
            
            if status == RegionStatus.HEALTHY:
                if self.active_region != region["name"]:
                    logging.info(f"Switching active region to: {region['name']}")
                    self.active_region = region["name"]
                    await self._notify_region_switch(region)
                return
                
        # If no healthy regions, try degraded
        for region in sorted_regions:
            status = self.region_status.get(region["name"], RegionStatus.FAILED)
            if status == RegionStatus.DEGRADED:
                if self.active_region != region["name"]:
                    logging.warning(f"Switching to degraded region: {region['name']}")
                    self.active_region = region["name"]
                    await self._notify_region_switch(region)
                return
                
        # All regions failed
        logging.critical("All regions failed! Manual intervention required.")
        
    async def get_active_endpoint(self) -> str:
        """Get the current active region endpoint"""
        if not self.active_region:
            return self.regions[0]["url"]  # Fallback to first region
            
        for region in self.regions:
            if region["name"] == self.active_region:
                return region["url"]
                
        return self.regions[0]["url"]
        
    async def _notify_region_switch(self, new_region: Dict):
        """Notify monitoring systems of region switch"""
        # Integration with monitoring/alerting systems
        alert_data = {
            "event": "region_switch",
            "new_region": new_region["name"],
            "timestamp": datetime.utcnow().isoformat(),
            "all_status": dict(self.region_status)
        }
        
        # Send to monitoring endpoint
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    os.getenv("MONITORING_WEBHOOK_URL"),
                    json=alert_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                )
        except Exception as e:
            logging.error(f"Failed to send region switch notification: {e}")
```

---

## 5) Advanced Observability

**`/enterprise/observability.py`**
```python
import asyncio
from typing import Dict, List
import json
from datetime import datetime, timedelta
import numpy as np

class UserJourneyMapper:
    """Track user interactions across sessions for insights"""
    def __init__(self, analytics_client):
        self.analytics = analytics_client
        
    async def track_journey_event(self, user_id: str, session_id: str, event_type: str, context: Dict):
        """Track a user journey event"""
        event = {
            "user_id": user_id,
            "session_id": session_id,
            "event_type": event_type,
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.analytics.track_event(event)
        
    async def analyze_user_patterns(self, user_id: str, days_back: int = 30) -> Dict:
        """Analyze user interaction patterns"""
        events = await self.analytics.get_user_events(user_id, days_back)
        
        return {
            "total_sessions": len(set(e["session_id"] for e in events)),
            "avg_session_length": self._calculate_avg_session_length(events),
            "preferred_models": self._analyze_model_preferences(events),
            "peak_usage_hours": self._analyze_usage_timing(events),
            "cost_trend": self._analyze_cost_trend(events),
            "quality_feedback": self._analyze_feedback_patterns(events)
        }

class PredictiveAnalytics:
    """Predict system behavior and optimize proactively"""
    def __init__(self, metrics_client):
        self.metrics = metrics_client
        
    async def predict_load(self, hours_ahead: int = 4) -> Dict:
        """Predict system load for capacity planning"""
        historical_data = await self.metrics.get_load_history(days=14)
        
        # Simple time-series prediction (replace with ML model)
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        
        predictions = []
        for h in range(hours_ahead):
            pred_hour = (current_hour + h) % 24
            pred_day = current_day if (current_hour + h) < 24 else (current_day + 1) % 7
            
            # Find similar historical patterns
            similar_periods = [
                d for d in historical_data 
                if d["hour"] == pred_hour and d["day_of_week"] == pred_day
            ]
            
            if similar_periods:
                avg_load = np.mean([p["request_rate"] for p in similar_periods])
                std_load = np.std([p["request_rate"] for p in similar_periods])
                
                predictions.append({
                    "hour": pred_hour,
                    "predicted_rps": avg_load,
                    "confidence_interval": [avg_load - std_load, avg_load + std_load],
                    "recommended_replicas": max(3, int(avg_load / 100))  # Rough scaling rule
                })
            else:
                predictions.append({
                    "hour": pred_hour,
                    "predicted_rps": 50,  # Default assumption
                    "confidence_interval": [30, 70],
                    "recommended_replicas": 3
                })
                
        return {
            "predictions": predictions,
            "current_load": await self.metrics.get_current_load(),
            "scaling_recommendations": self._generate_scaling_recommendations(predictions)
        }
        
    def _generate_scaling_recommendations(self, predictions: List[Dict]) -> List[str]:
        """Generate actionable scaling recommendations"""
        recommendations = []
        
        max_predicted = max(p["predicted_rps"] for p in predictions)
        current_capacity = 300  # Assume current capacity
        
        if max_predicted > current_capacity * 0.8:
            recommendations.append(f"Scale up: predicted peak of {max_predicted} RPS exceeds 80% capacity")
            
        peak_hour = max(predictions, key=lambda p: p["predicted_rps"])["hour"]
        recommendations.append(f"Schedule scaling at {peak_hour}:00 for predicted peak load")
        
        return recommendations

class CostOptimizer:
    """Analyze usage patterns and suggest cost optimizations"""
    def __init__(self, usage_tracker):
        self.usage_tracker = usage_tracker
        
    async def analyze_cost_efficiency(self, tenant_id: str) -> Dict:
        """Analyze cost efficiency and suggest optimizations"""
        usage_data = await self.usage_tracker.get_detailed_usage(tenant_id, days=30)
        
        analysis = {
            "current_spend": sum(d["total_cost"] for d in usage_data),
            "model_breakdown": self._analyze_model_costs(usage_data),
            "waste_analysis": self._identify_waste(usage_data),
            "optimization_opportunities": self._suggest_optimizations(usage_data),
            "projected_savings": self._calculate_projected_savings(usage_data)
        }
        
        return analysis
        
    def _identify_waste(self, usage_data: List[Dict]) -> Dict:
        """Identify wasteful usage patterns"""
        waste_indicators = {
            "duplicate_requests": 0,
            "overprovisioned_models": 0,
            "low_cache_hit_rate": False,
            "peak_hour_waste": 0
        }
        
        # Analyze for duplicate requests (same user, similar content, short time gap)
        # Analyze for expensive models used on simple tasks
        # Check cache hit rates
        
        return waste_indicators
        
    def _suggest_optimizations(self, usage_data: List[Dict]) -> List[str]:
        """Generate specific cost optimization suggestions"""
        suggestions = []
        
        # Model usage analysis
        model_costs = self._analyze_model_costs(usage_data)
        total_requests = sum(d["request_count"] for d in usage_data)
        
        # Check for expensive model overuse
        expensive_models = ["gpt-5", "claude-3-7"]
        expensive_usage = sum(model_costs.get(model, {}).get("count", 0) for model in expensive_models)
        
        if expensive_usage > total_requests * 0.3:
            suggestions.append(
                f"Consider routing more requests to cheaper models. {expensive_usage} out of {total_requests} "
                f"requests use premium models. Potential savings: ${self._calculate_model_savings(model_costs):.2f}/month"
            )
        
        # Cache hit rate analysis
        cache_hit_rate = self._calculate_cache_hit_rate(usage_data)
        if cache_hit_rate < 0.2:
            suggestions.append(
                f"Improve cache hit rate (currently {cache_hit_rate:.1%}). "
                f"Enable semantic caching for ~30% cost reduction on repeated queries."
            )
            
        # Peak hour analysis
        peak_costs = self._analyze_peak_hour_costs(usage_data)
        if peak_costs["off_peak_opportunity"] > 0.15:
            suggestions.append(
                f"Consider batch processing non-urgent requests during off-peak hours. "
                f"Potential savings: ${peak_costs['potential_savings']:.2f}/month"
            )
            
        return suggestions