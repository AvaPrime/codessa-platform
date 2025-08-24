# Comprehensive security hardening configuration
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class SecurityLevel(Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    HIGH = "high"
    MAXIMUM = "maximum"

@dataclass
class SecurityHardeningConfig:
    """Security hardening configuration"""
    security_level: SecurityLevel = SecurityLevel.HIGH
    
    # Authentication & Authorization
    enforce_mfa: bool = True
    password_min_length: int = 14
    password_complexity_required: bool = True
    session_timeout_minutes: int = 30
    max_concurrent_sessions: int = 3
    
    # Network Security
    enable_tls_everywhere: bool = True
    min_tls_version: str = "1.3"
    disable_weak_ciphers: bool = True
    enable_hsts: bool = True
    
    # Data Protection
    encrypt_at_rest: bool = True
    encrypt_in_transit: bool = True
    data_classification_required: bool = True
    
    # Monitoring & Auditing
    enable_security_logging: bool = True
    log_all_access_attempts: bool = True
    enable_behavioral_analysis: bool = True
    
    # Incident Response
    auto_incident_response: bool = True
    quarantine_suspicious_activity: bool = True
    
    def get_security_policies(self) -> Dict[str, any]:
        """Get security policies based on security level"""
        policies = {
            SecurityLevel.MINIMAL: {
                "rate_limit_requests_per_minute": 1000,
                "failed_login_lockout_attempts": 10,
                "session_timeout_minutes": 120,
                "password_min_length": 8
            },
            SecurityLevel.STANDARD: {
                "rate_limit_requests_per_minute": 500,
                "failed_login_lockout_attempts": 5,
                "session_timeout_minutes": 60,
                "password_min_length": 10
            },
            SecurityLevel.HIGH: {
                "rate_limit_requests_per_minute": 200,
                "failed_login_lockout_attempts": 3,
                "session_timeout_minutes": 30,
                "password_min_length": 12
            },
            SecurityLevel.MAXIMUM: {
                "rate_limit_requests_per_minute": 100,
                "failed_login_lockout_attempts": 2,
                "session_timeout_minutes": 15,
                "password_min_length": 16
            }
        }
        return policies[self.security_level]

# Global security configuration
SECURITY_CONFIG = SecurityHardeningConfig(
    security_level=SecurityLevel(os.getenv("SECURITY_LEVEL", "high"))
)