# Enhanced security monitoring and threat detection
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import aioredis
import numpy as np
from collections import defaultdict, deque

class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityAlert:
    alert_id: str
    threat_level: ThreatLevel
    event_type: str
    description: str
    indicators: List[str]
    affected_resources: List[str]
    timestamp: datetime
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None

class BehavioralAnalyzer:
    def __init__(self):
        self.user_baselines = {}
        self.ip_baselines = {}
        self.system_baselines = {}
        self.anomaly_threshold = 2.5  # Standard deviations
    
    async def analyze_user_behavior(self, user_id: str, 
                                  activity: Dict[str, Any]) -> Optional[SecurityAlert]:
        """Analyze user behavior for anomalies"""
        if user_id not in self.user_baselines:
            self.user_baselines[user_id] = {
                'login_times': deque(maxlen=100),
                'request_patterns': defaultdict(int),
                'ip_addresses': set(),
                'failed_attempts': deque(maxlen=50)
            }
        
        baseline = self.user_baselines[user_id]
        current_time = datetime.now()
        
        # Check for unusual login times
        if activity.get('event_type') == 'login':
            hour = current_time.hour
            baseline['login_times'].append(hour)
            
            if len(baseline['login_times']) > 10:
                avg_hour = np.mean(baseline['login_times'])
                std_hour = np.std(baseline['login_times'])
                
                if abs(hour - avg_hour) > self.anomaly_threshold * std_hour:
                    return SecurityAlert(
                        alert_id=f"anomaly_{user_id}_{int(current_time.timestamp())}",
                        threat_level=ThreatLevel.MEDIUM,
                        event_type="unusual_login_time",
                        description=f"User {user_id} logged in at unusual time: {hour}:00",
                        indicators=[f"login_time:{hour}", f"avg_time:{avg_hour:.1f}"],
                        affected_resources=[f"user:{user_id}"],
                        timestamp=current_time,
                        user_id=user_id,
                        source_ip=activity.get('ip_address')
                    )
        
        # Check for new IP addresses
        if 'ip_address' in activity:
            ip = activity['ip_address']
            if ip not in baseline['ip_addresses']:
                baseline['ip_addresses'].add(ip)
                
                # Alert if user has used many different IPs recently
                if len(baseline['ip_addresses']) > 5:
                    return SecurityAlert(
                        alert_id=f"multi_ip_{user_id}_{int(current_time.timestamp())}",
                        threat_level=ThreatLevel.HIGH,
                        event_type="multiple_ip_addresses",
                        description=f"User {user_id} accessed from {len(baseline['ip_addresses'])} different IPs",
                        indicators=[f"ip_count:{len(baseline['ip_addresses'])}", f"latest_ip:{ip}"],
                        affected_resources=[f"user:{user_id}"],
                        timestamp=current_time,
                        user_id=user_id,
                        source_ip=ip
                    )
        
        return None
    
    async def analyze_system_metrics(self, metrics: Dict[str, float]) -> List[SecurityAlert]:
        """Analyze system metrics for security anomalies"""
        alerts = []
        current_time = datetime.now()
        
        # Check for unusual resource usage patterns
        if metrics.get('cpu_usage', 0) > 90:
            alerts.append(SecurityAlert(
                alert_id=f"high_cpu_{int(current_time.timestamp())}",
                threat_level=ThreatLevel.HIGH,
                event_type="resource_exhaustion",
                description=f"High CPU usage detected: {metrics['cpu_usage']:.1f}%",
                indicators=[f"cpu_usage:{metrics['cpu_usage']}"],
                affected_resources=["system:cpu"],
                timestamp=current_time
            ))
        
        # Check for unusual network activity
        if metrics.get('network_connections', 0) > 1000:
            alerts.append(SecurityAlert(
                alert_id=f"high_connections_{int(current_time.timestamp())}",
                threat_level=ThreatLevel.MEDIUM,
                event_type="unusual_network_activity",
                description=f"High number of network connections: {metrics['network_connections']}",
                indicators=[f"connections:{metrics['network_connections']}"],
                affected_resources=["system:network"],
                timestamp=current_time
            ))
        
        return alerts

class EnhancedSecurityMonitor:
    def __init__(self):
        self.redis = None
        self.behavioral_analyzer = BehavioralAnalyzer()
        self.alert_handlers = {
            ThreatLevel.LOW: self._handle_low_threat,
            ThreatLevel.MEDIUM: self._handle_medium_threat,
            ThreatLevel.HIGH: self._handle_high_threat,
            ThreatLevel.CRITICAL: self._handle_critical_threat
        }
    
    async def initialize(self):
        """Initialize enhanced security monitoring"""
        self.redis = aioredis.from_url("redis://redis:6379")
        
        # Start background monitoring tasks
        asyncio.create_task(self._monitor_failed_logins())
        asyncio.create_task(self._monitor_system_metrics())
        asyncio.create_task(self._monitor_suspicious_patterns())
    
    async def process_security_event(self, event: Dict[str, Any]):
        """Process incoming security event"""
        # Behavioral analysis
        if event.get('user_id'):
            alert = await self.behavioral_analyzer.analyze_user_behavior(
                event['user_id'], event
            )
            if alert:
                await self._handle_alert(alert)
        
        # Pattern-based detection
        alerts = await self._detect_attack_patterns(event)
        for alert in alerts:
            await self._handle_alert(alert)
        
        # Store event for analysis
        await self._store_security_event(event)
    
    async def _detect_attack_patterns(self, event: Dict[str, Any]) -> List[SecurityAlert]:
        """Detect common attack patterns"""
        alerts = []
        current_time = datetime.now()
        
        # Brute force detection
        if event.get('event_type') == 'failed_login':
            ip = event.get('ip_address')
            if ip:
                key = f"failed_logins:{ip}"
                count = await self.redis.incr(key)
                await self.redis.expire(key, 300)  # 5 minute window
                
                if count >= 10:  # 10 failed attempts in 5 minutes
                    alerts.append(SecurityAlert(
                        alert_id=f"brute_force_{ip}_{int(current_time.timestamp())}",
                        threat_level=ThreatLevel.HIGH,
                        event_type="brute_force_attack",
                        description=f"Brute force attack detected from IP {ip}",
                        indicators=[f"failed_attempts:{count}", f"time_window:5min"],
                        affected_resources=["system:authentication"],
                        timestamp=current_time,
                        source_ip=ip
                    ))
        
        # SQL injection detection
        if 'sql' in event.get('request_data', '').lower():
            sql_keywords = ['union', 'select', 'drop', 'insert', 'delete', 'update']
            request_data = event.get('request_data', '').lower()
            
            if any(keyword in request_data for keyword in sql_keywords):
                alerts.append(SecurityAlert(
                    alert_id=f"sql_injection_{int(current_time.timestamp())}",
                    threat_level=ThreatLevel.CRITICAL,
                    event_type="sql_injection_attempt",
                    description="Potential SQL injection attempt detected",
                    indicators=["sql_keywords_detected"],
                    affected_resources=["system:database"],
                    timestamp=current_time,
                    source_ip=event.get('ip_address'),
                    user_id=event.get('user_id')
                ))
        
        return alerts
    
    async def _handle_alert(self, alert: SecurityAlert):
        """Handle security alert based on threat level"""
        # Store alert
        await self._store_alert(alert)
        
        # Execute threat-specific handler
        handler = self.alert_handlers.get(alert.threat_level)
        if handler:
            await handler(alert)
    
    async def _handle_critical_threat(self, alert: SecurityAlert):
        """Handle critical threat - immediate response"""
        # Auto-quarantine if applicable
        if alert.source_ip:
            await self._quarantine_ip(alert.source_ip)
        
        if alert.user_id:
            await self._suspend_user(alert.user_id)
        
        # Immediate notification
        await self._send_immediate_notification(alert)
        
        # Trigger incident response
        from .incident_response import IncidentResponseSystem
        incident_system = IncidentResponseSystem()
        await incident_system.create_incident(
            title=f"Critical Security Alert: {alert.event_type}",
            description=alert.description,
            severity="P0",
            affected_systems=alert.affected_resources,
            indicators=alert.indicators
        )