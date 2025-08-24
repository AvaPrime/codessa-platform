# Security event monitoring and alerting
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
import aioredis
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class SecurityEventType(Enum):
    FAILED_LOGIN = "failed_login"
    SUCCESSFUL_LOGIN = "successful_login"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MALWARE_DETECTION = "malware_detection"
    NETWORK_INTRUSION = "network_intrusion"

class SecuritySeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    event_type: SecurityEventType
    severity: SecuritySeverity
    timestamp: datetime
    user_id: str
    ip_address: str
    user_agent: str
    description: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data

class SecurityMonitor:
    def __init__(self):
        self.redis = None
        self.logger = logging.getLogger('security_monitor')
        self.alert_thresholds = {
            SecurityEventType.FAILED_LOGIN: {'count': 5, 'window': 300},  # 5 in 5 minutes
            SecurityEventType.UNAUTHORIZED_ACCESS: {'count': 3, 'window': 300},
            SecurityEventType.SUSPICIOUS_ACTIVITY: {'count': 1, 'window': 60},
        }
    
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis = await aioredis.from_url("redis://localhost:6379")
    
    async def log_security_event(self, event: SecurityEvent):
        """Log security event and check for alerts"""
        # Store event
        event_key = f"security_event:{event.timestamp.isoformat()}"
        await self.redis.setex(event_key, 86400, json.dumps(event.to_dict()))  # 24 hours
        
        # Add to event type index
        type_key = f"security_events:{event.event_type.value}"
        await self.redis.zadd(type_key, {event_key: event.timestamp.timestamp()})
        await self.redis.expire(type_key, 86400)
        
        # Add to user index
        user_key = f"security_events:user:{event.user_id}"
        await self.redis.zadd(user_key, {event_key: event.timestamp.timestamp()})
        await self.redis.expire(user_key, 86400)
        
        # Add to IP index
        ip_key = f"security_events:ip:{event.ip_address}"
        await self.redis.zadd(ip_key, {event_key: event.timestamp.timestamp()})
        await self.redis.expire(ip_key, 86400)
        
        # Check for alert conditions
        await self._check_alert_conditions(event)
        
        self.logger.info(f"Security event logged: {event.event_type.value} - {event.description}")
    
    async def _check_alert_conditions(self, event: SecurityEvent):
        """Check if event triggers any alerts"""
        if event.event_type in self.alert_thresholds:
            threshold = self.alert_thresholds[event.event_type]
            
            # Check event count in time window
            since = datetime.now() - timedelta(seconds=threshold['window'])
            
            # Check by user
            user_key = f"security_events:user:{event.user_id}"
            user_count = await self.redis.zcount(user_key, since.timestamp(), '+inf')
            
            if user_count >= threshold['count']:
                await self._trigger_alert(f"User {event.user_id} exceeded {event.event_type.value} threshold", 
                                        SecuritySeverity.HIGH, event)
            
            # Check by IP
            ip_key = f"security_events:ip:{event.ip_address}"
            ip_count = await self.redis.zcount(ip_key, since.timestamp(), '+inf')
            
            if ip_count >= threshold['count']:
                await self._trigger_alert(f"IP {event.ip_address} exceeded {event.event_type.value} threshold", 
                                        SecuritySeverity.HIGH, event)
    
    async def _trigger_alert(self, message: str, severity: SecuritySeverity, event: SecurityEvent):
        """Trigger security alert"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'severity': severity.value,
            'triggering_event': event.to_dict()
        }
        
        # Store alert
        alert_key = f"security_alert:{datetime.now().isoformat()}"
        await self.redis.setex(alert_key, 86400 * 7, json.dumps(alert))  # 7 days
        
        # Send notifications
        await self._send_alert_notification(alert)
        
        self.logger.critical(f"Security alert triggered: {message}")
    
    async def _send_alert_notification(self, alert: Dict[str, Any]):
        """Send alert notification via email/Slack"""
        # Email notification
        try:
            await self._send_email_alert(alert)
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
        
        # Slack notification
        try:
            await self._send_slack_alert(alert)
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
    
    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Send email alert"""
        smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        alert_email = os.getenv('SECURITY_ALERT_EMAIL')
        
        if not all([smtp_user, smtp_password, alert_email]):
            return
        
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = alert_email
        msg['Subject'] = f"Security Alert - {alert['severity'].upper()}"
        
        body = f"""
        Security Alert Triggered
        
        Time: {alert['timestamp']}
        Severity: {alert['severity'].upper()}
        Message: {alert['message']}
        
        Triggering Event:
        {json.dumps(alert['triggering_event'], indent=2)}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    
    async def _send_slack_alert(self, alert: Dict[str, Any]):
        """Send Slack alert"""
        webhook_url = os.getenv('SLACK_SECURITY_WEBHOOK')
        if not webhook_url:
            return
        
        import aiohttp
        
        color = {
            'low': '#36a64f',
            'medium': '#ff9500',
            'high': '#ff0000',
            'critical': '#8b0000'
        }.get(alert['severity'], '#ff0000')
        
        payload = {
            'attachments': [{
                'color': color,
                'title': f"Security Alert - {alert['severity'].upper()}",
                'text': alert['message'],
                'fields': [
                    {'title': 'Time', 'value': alert['timestamp'], 'short': True},
                    {'title': 'Severity', 'value': alert['severity'].upper(), 'short': True}
                ],
                'footer': 'Multi-Agent Factory Security Monitor'
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json=payload)
    
    async def get_security_events(self, 
                                event_type: SecurityEventType = None,
                                user_id: str = None,
                                ip_address: str = None,
                                since: datetime = None,
                                limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve security events with filters"""
        if since is None:
            since = datetime.now() - timedelta(hours=24)
        
        # Determine which index to use
        if event_type:
            key = f"security_events:{event_type.value}"
        elif user_id:
            key = f"security_events:user:{user_id}"
        elif ip_address:
            key = f"security_events:ip:{ip_address}"
        else:
            # Get all events (this could be expensive)
            key = "security_events:*"
        
        # Get event keys
        event_keys = await self.redis.zrevrangebyscore(
            key, '+inf', since.timestamp(), start=0, num=limit
        )
        
        # Retrieve events
        events = []
        for event_key in event_keys:
            event_data = await self.redis.get(event_key)
            if event_data:
                events.append(json.loads(event_data))
        
        return events

# Security event decorators
def log_security_event(event_type: SecurityEventType, severity: SecuritySeverity = SecuritySeverity.MEDIUM):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request info
            request = kwargs.get('request')
            user = kwargs.get('current_user')
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful event if needed
                if event_type == SecurityEventType.SUCCESSFUL_LOGIN:
                    monitor = SecurityMonitor()
                    await monitor.initialize()
                    
                    event = SecurityEvent(
                        event_type=event_type,
                        severity=severity,
                        timestamp=datetime.now(),
                        user_id=user.id if user else 'anonymous',
                        ip_address=request.client.host if request else 'unknown',
                        user_agent=request.headers.get('user-agent', '') if request else '',
                        description=f"Successful {func.__name__}",
                        metadata={'function': func.__name__}
                    )
                    
                    await monitor.log_security_event(event)
                
                return result
                
            except Exception as e:
                # Log failed event
                monitor = SecurityMonitor()
                await monitor.initialize()
                
                event = SecurityEvent(
                    event_type=SecurityEventType.FAILED_LOGIN if 'login' in func.__name__ else SecurityEventType.UNAUTHORIZED_ACCESS,
                    severity=SecuritySeverity.HIGH,
                    timestamp=datetime.now(),
                    user_id=user.id if user else 'anonymous',
                    ip_address=request.client.host if request else 'unknown',
                    user_agent=request.headers.get('user-agent', '') if request else '',
                    description=f"Failed {func.__name__}: {str(e)}",
                    metadata={'function': func.__name__, 'error': str(e)}
                )
                
                await monitor.log_security_event(event)
                raise
        
        return wrapper
    return decorator