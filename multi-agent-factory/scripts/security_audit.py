#!/usr/bin/env python3
# Comprehensive security audit and compliance checker

import os
import json
import subprocess
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import requests
import hashlib

class ComplianceFramework(Enum):
    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"

class AuditSeverity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditFinding:
    id: str
    title: str
    description: str
    severity: AuditSeverity
    category: str
    compliance_frameworks: List[ComplianceFramework]
    remediation: str
    evidence: Dict[str, Any]
    timestamp: datetime

class SecurityAuditor:
    def __init__(self):
        self.findings = []
        self.compliance_checks = {
            ComplianceFramework.SOC2: self._check_soc2_compliance,
            ComplianceFramework.GDPR: self._check_gdpr_compliance,
            ComplianceFramework.ISO27001: self._check_iso27001_compliance
        }
    
    def run_comprehensive_audit(self) -> Dict[str, Any]:
        """Run comprehensive security audit"""
        print("Starting comprehensive security audit...")
        
        # Infrastructure security checks
        self._audit_infrastructure_security()
        
        # Application security checks
        self._audit_application_security()
        
        # Data protection checks
        self._audit_data_protection()
        
        # Access control checks
        self._audit_access_controls()
        
        # Monitoring and logging checks
        self._audit_monitoring_logging()
        
        # Compliance checks
        self._audit_compliance()
        
        # Generate report
        return self._generate_audit_report()
    
    def _audit_infrastructure_security(self):
        """Audit infrastructure security configuration"""
        print("Auditing infrastructure security...")
        
        # Check Docker security
        self._check_docker_security()
        
        # Check network security
        self._check_network_security()
        
        # Check TLS configuration
        self._check_tls_configuration()
        
        # Check firewall rules
        self._check_firewall_configuration()
    
    def _check_docker_security(self):
        """Check Docker security configuration"""
        try:
            # Check if Docker daemon is running as root
            result = subprocess.run(['docker', 'info'], 
                                  capture_output=True, text=True)
            
            if 'rootless' not in result.stdout.lower():
                self.findings.append(AuditFinding(
                    id="DOCKER_001",
                    title="Docker running as root",
                    description="Docker daemon is running as root user",
                    severity=AuditSeverity.MEDIUM,
                    category="Infrastructure",
                    compliance_frameworks=[ComplianceFramework.SOC2],
                    remediation="Configure Docker to run in rootless mode",
                    evidence={"docker_info": result.stdout[:500]},
                    timestamp=datetime.now()
                ))
            
            # Check Docker Compose security
            if os.path.exists('docker-compose.yml'):
                with open('docker-compose.yml', 'r') as f:
                    compose_config = yaml.safe_load(f)
                
                # Check for privileged containers
                for service_name, service_config in compose_config.get('services', {}).items():
                    if service_config.get('privileged', False):
                        self.findings.append(AuditFinding(
                            id=f"DOCKER_002_{service_name}",
                            title=f"Privileged container: {service_name}",
                            description=f"Service {service_name} is running in privileged mode",
                            severity=AuditSeverity.HIGH,
                            category="Infrastructure",
                            compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
                            remediation="Remove privileged mode and use specific capabilities instead",
                            evidence={"service": service_name, "config": service_config},
                            timestamp=datetime.now()
                        ))
                
        except Exception as e:
            print(f"Error checking Docker security: {e}")
    
    def _check_tls_configuration(self):
        """Check TLS configuration"""
        # Check if HTTPS is enforced
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_content = f.read()
            
            if 'FORCE_HTTPS=true' not in env_content:
                self.findings.append(AuditFinding(
                    id="TLS_001",
                    title="HTTPS not enforced",
                    description="HTTPS is not enforced in environment configuration",
                    severity=AuditSeverity.HIGH,
                    category="Network Security",
                    compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.GDPR],
                    remediation="Set FORCE_HTTPS=true in environment configuration",
                    evidence={"env_file_exists": True},
                    timestamp=datetime.now()
                ))
    
    def _audit_application_security(self):
        """Audit application security"""
        print("Auditing application security...")
        
        # Check authentication configuration
        self._check_authentication_config()
        
        # Check authorization configuration
        self._check_authorization_config()
        
        # Check input validation
        self._check_input_validation()
        
        # Check error handling
        self._check_error_handling()
    
    def _check_authentication_config(self):
        """Check authentication configuration"""
        auth_file = 'api/auth.py'
        if os.path.exists(auth_file):
            with open(auth_file, 'r') as f:
                auth_content = f.read()
            
            # Check for weak JWT secret
            if 'your-super-secret-jwt-key-change-this-in-production' in auth_content:
                self.findings.append(AuditFinding(
                    id="AUTH_001",
                    title="Default JWT secret in use",
                    description="Default JWT secret is still in use",
                    severity=AuditSeverity.CRITICAL,
                    category="Authentication",
                    compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.GDPR],
                    remediation="Generate a strong, unique JWT secret",
                    evidence={"file": auth_file},
                    timestamp=datetime.now()
                ))
            
            # Check for MFA implementation
            if 'MFA' not in auth_content and 'totp' not in auth_content.lower():
                self.findings.append(AuditFinding(
                    id="AUTH_002",
                    title="Multi-factor authentication not implemented",
                    description="MFA is not implemented for user authentication",
                    severity=AuditSeverity.HIGH,
                    category="Authentication",
                    compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
                    remediation="Implement multi-factor authentication",
                    evidence={"file": auth_file},
                    timestamp=datetime.now()
                ))
    
    def _audit_data_protection(self):
        """Audit data protection measures"""
        print("Auditing data protection...")
        
        # Check encryption configuration
        encryption_file = 'security/encryption.py'
        if os.path.exists(encryption_file):
            with open(encryption_file, 'r') as f:
                encryption_content = f.read()
            
            # Check for proper key management
            if '/etc/maf/master.key' in encryption_content:
                # Check if key file exists and has proper permissions
                key_file = '/etc/maf/master.key'
                if os.path.exists(key_file):
                    stat_info = os.stat(key_file)
                    if stat_info.st_mode & 0o077:  # Check if group/other have any permissions
                        self.findings.append(AuditFinding(
                            id="DATA_001",
                            title="Insecure key file permissions",
                            description="Master key file has overly permissive permissions",
                            severity=AuditSeverity.HIGH,
                            category="Data Protection",
                            compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.GDPR],
                            remediation="Set key file permissions to 600 (owner read/write only)",
                            evidence={"file": key_file, "permissions": oct(stat_info.st_mode)},
                            timestamp=datetime.now()
                        ))
        
        # Check database encryption
        self._check_database_encryption()
    
    def _check_database_encryption(self):
        """Check database encryption configuration"""
        compose_file = 'infra/docker/docker-compose.yml'
        if os.path.exists(compose_file):
            with open(compose_file, 'r') as f:
                compose_config = yaml.safe_load(f)
            
            db_service = compose_config.get('services', {}).get('db', {})
            db_env = db_service.get('environment', [])
            
            # Check if database encryption is enabled
            encryption_enabled = any('POSTGRES_INITDB_ARGS' in str(env) and 'encryption' in str(env) 
                                   for env in db_env)
            
            if not encryption_enabled:
                self.findings.append(AuditFinding(
                    id="DATA_002",
                    title="Database encryption not configured",
                    description="PostgreSQL database encryption at rest is not configured",
                    severity=AuditSeverity.MEDIUM,
                    category="Data Protection",
                    compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.HIPAA],
                    remediation="Configure PostgreSQL with encryption at rest",
                    evidence={"db_config": db_service},
                    timestamp=datetime.now()
                ))
    
    def _audit_compliance(self):
        """Run compliance-specific checks"""
        print("Auditing compliance requirements...")
        
        for framework, check_func in self.compliance_checks.items():
            try:
                check_func()
            except Exception as e:
                print(f"Error checking {framework.value} compliance: {e}")
    
    def _check_soc2_compliance(self):
        """Check SOC 2 compliance requirements"""
        # Check logging and monitoring
        if not os.path.exists('security/monitoring.py'):
            self.findings.append(AuditFinding(
                id="SOC2_001",
                title="Security monitoring not implemented",
                description="Security event monitoring is required for SOC 2 compliance",
                severity=AuditSeverity.HIGH,
                category="Compliance",
                compliance_frameworks=[ComplianceFramework.SOC2],
                remediation="Implement comprehensive security monitoring",
                evidence={"monitoring_file_exists": False},
                timestamp=datetime.now()
            ))
        
        # Check incident response procedures
        if not os.path.exists('docs/runbooks/INCIDENT_RESPONSE.md'):
            self.findings.append(AuditFinding(
                id="SOC2_002",
                title="Incident response procedures not documented",
                description="Documented incident response procedures are required for SOC 2",
                severity=AuditSeverity.MEDIUM,
                category="Compliance",
                compliance_frameworks=[ComplianceFramework.SOC2],
                remediation="Document incident response procedures",
                evidence={"incident_response_docs_exist": False},
                timestamp=datetime.now()
            ))
    
    def _check_gdpr_compliance(self):
        """Check GDPR compliance requirements"""
        # Check data retention policies
        if not os.path.exists('docs/DATA_RETENTION_POLICY.md'):
            self.findings.append(AuditFinding(
                id="GDPR_001",
                title="Data retention policy not documented",
                description="GDPR requires documented data retention policies",
                severity=AuditSeverity.HIGH,
                category="Compliance",
                compliance_frameworks=[ComplianceFramework.GDPR],
                remediation="Document data retention and deletion policies",
                evidence={"retention_policy_exists": False},
                timestamp=datetime.now()
            ))
        
        # Check privacy controls
        api_files = ['api/main.py', 'api/auth.py']
        privacy_controls_found = False
        
        for file_path in api_files:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    if 'privacy' in content.lower() or 'gdpr' in content.lower():
                        privacy_controls_found = True
                        break
        
        if not privacy_controls_found:
            self.findings.append(AuditFinding(
                id="GDPR_002",
                title="Privacy controls not implemented",
                description="GDPR requires privacy controls and data subject rights",
                severity=AuditSeverity.HIGH,
                category="Compliance",
                compliance_frameworks=[ComplianceFramework.GDPR],
                remediation="Implement privacy controls and data subject rights endpoints",
                evidence={"api_files_checked": api_files},
                timestamp=datetime.now()
            ))
    
    def _generate_audit_report(self) -> Dict[str, Any]:
        """Generate comprehensive audit report"""
        # Categorize findings by severity
        severity_counts = {severity: 0 for severity in AuditSeverity}
        for finding in self.findings:
            severity_counts[finding.severity] += 1
        
        # Calculate risk score
        risk_score = (
            severity_counts[AuditSeverity.CRITICAL] * 10 +
            severity_counts[AuditSeverity.HIGH] * 7 +
            severity_counts[AuditSeverity.MEDIUM] * 4 +
            severity_counts[AuditSeverity.LOW] * 2 +
            severity_counts[AuditSeverity.INFO] * 1
        )
        
        report = {
            "audit_timestamp": datetime.now().isoformat(),
            "total_findings": len(self.findings),
            "severity_breakdown": {k.value: v for k, v in severity_counts.items()},
            "risk_score": risk_score,
            "risk_level": self._calculate_risk_level(risk_score),
            "findings": [asdict(finding) for finding in self.findings],
            "recommendations": self._generate_recommendations()
        }
        
        # Save report
        report_file = f"security_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nAudit completed. Report saved to: {report_file}")
        print(f"Total findings: {len(self.findings)}")
        print(f"Risk score: {risk_score} ({self._calculate_risk_level(risk_score)})")
        
        return report
    
    def _calculate_risk_level(self, risk_score: int) -> str:
        """Calculate overall risk level"""
        if risk_score >= 50:
            return "CRITICAL"
        elif risk_score >= 30:
            return "HIGH"
        elif risk_score >= 15:
            return "MEDIUM"
        elif risk_score >= 5:
            return "LOW"
        else:
            return "MINIMAL"
    
    def _generate_recommendations(self) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []
        
        # Critical findings first
        critical_findings = [f for f in self.findings if f.severity == AuditSeverity.CRITICAL]
        if critical_findings:
            recommendations.append("IMMEDIATE ACTION REQUIRED: Address all critical security findings")
        
        # High severity findings
        high_findings = [f for f in self.findings if f.severity == AuditSeverity.HIGH]
        if high_findings:
            recommendations.append("HIGH PRIORITY: Remediate high-severity security issues within 7 days")
        
        # Compliance-specific recommendations
        compliance_findings = [f for f in self.findings if f.compliance_frameworks]
        if compliance_findings:
            recommendations.append("COMPLIANCE: Address compliance-related findings for regulatory requirements")
        
        return recommendations

if __name__ == '__main__':
    auditor = SecurityAuditor()
    report = auditor.run_comprehensive_audit()