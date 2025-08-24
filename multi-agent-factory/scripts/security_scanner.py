#!/usr/bin/env python3
# Automated security vulnerability scanner

import subprocess
import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any
import requests

class SecurityScanner:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'vulnerabilities': [],
            'summary': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }
    
    def scan_python_dependencies(self):
        """Scan Python dependencies for vulnerabilities"""
        print("Scanning Python dependencies...")
        
        try:
            # Use safety to check for known vulnerabilities
            result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.stdout:
                vulnerabilities = json.loads(result.stdout)
                for vuln in vulnerabilities:
                    self.results['vulnerabilities'].append({
                        'type': 'python_dependency',
                        'package': vuln.get('package'),
                        'version': vuln.get('installed_version'),
                        'vulnerability_id': vuln.get('vulnerability_id'),
                        'severity': self._map_severity(vuln.get('severity', 'medium')),
                        'description': vuln.get('advisory'),
                        'fix_version': vuln.get('fix_version')
                    })
                    
                    severity = self._map_severity(vuln.get('severity', 'medium'))
                    self.results['summary'][severity] += 1
        
        except Exception as e:
            print(f"Error scanning Python dependencies: {e}")
    
    def scan_docker_images(self):
        """Scan Docker images for vulnerabilities"""
        print("Scanning Docker images...")
        
        images = [
            'multi-agent-factory:latest',
            'postgres:15-alpine',
            'redis:7-alpine',
            'nats:alpine'
        ]
        
        for image in images:
            try:
                result = subprocess.run(
                    ['trivy', 'image', '--format', 'json', image],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.stdout:
                    scan_result = json.loads(result.stdout)
                    for result_item in scan_result.get('Results', []):
                        for vuln in result_item.get('Vulnerabilities', []):
                            self.results['vulnerabilities'].append({
                                'type': 'container_vulnerability',
                                'image': image,
                                'package': vuln.get('PkgName'),
                                'version': vuln.get('InstalledVersion'),
                                'vulnerability_id': vuln.get('VulnerabilityID'),
                                'severity': vuln.get('Severity', 'UNKNOWN').lower(),
                                'description': vuln.get('Description'),
                                'fix_version': vuln.get('FixedVersion')
                            })
                            
                            severity = vuln.get('Severity', 'UNKNOWN').lower()
                            if severity in self.results['summary']:
                                self.results['summary'][severity] += 1
            
            except Exception as e:
                print(f"Error scanning image {image}: {e}")
    
    def scan_infrastructure(self):
        """Scan infrastructure configuration"""
        print("Scanning infrastructure configuration...")
        
        # Check for common misconfigurations
        misconfigurations = []
        
        # Check Docker Compose security
        compose_file = 'infra/docker/docker-compose.yml'
        if os.path.exists(compose_file):
            with open(compose_file, 'r') as f:
                content = f.read()
                
                if 'privileged: true' in content:
                    misconfigurations.append({
                        'type': 'infrastructure_misconfiguration',
                        'severity': 'high',
                        'description': 'Privileged containers detected',
                        'file': compose_file,
                        'recommendation': 'Remove privileged: true unless absolutely necessary'
                    })
                
                if 'security_opt' not in content:
                    misconfigurations.append({
                        'type': 'infrastructure_misconfiguration',
                        'severity': 'medium',
                        'description': 'Missing security options in containers',
                        'file': compose_file,
                        'recommendation': 'Add security_opt: ["no-new-privileges:true"]'
                    })
        
        for config in misconfigurations:
            self.results['vulnerabilities'].append(config)
            self.results['summary'][config['severity']] += 1
    
    def _map_severity(self, severity: str) -> str:
        """Map various severity formats to standard levels"""
        severity_lower = severity.lower()
        if severity_lower in ['critical', 'high', 'medium', 'low']:
            return severity_lower
        elif severity_lower in ['error', 'fatal']:
            return 'critical'
        elif severity_lower in ['warning', 'warn']:
            return 'medium'
        elif severity_lower in ['info', 'informational']:
            return 'low'
        else:
            return 'medium'
    
    def generate_report(self) -> str:
        """Generate security scan report"""
        report = f"""
# Security Scan Report

**Scan Date:** {self.results['timestamp']}

## Summary
- Critical: {self.results['summary']['critical']}
- High: {self.results['summary']['high']}
- Medium: {self.results['summary']['medium']}
- Low: {self.results['summary']['low']}

## Vulnerabilities

"""
        
        for vuln in sorted(self.results['vulnerabilities'], 
                          key=lambda x: ['critical', 'high', 'medium', 'low'].index(x.get('severity', 'low'))):
            report += f"""
### {vuln.get('vulnerability_id', 'N/A')} - {vuln.get('severity', 'unknown').upper()}

- **Type:** {vuln.get('type', 'unknown')}
- **Package:** {vuln.get('package', 'N/A')}
- **Version:** {vuln.get('version', 'N/A')}
- **Description:** {vuln.get('description', 'No description available')}
- **Fix:** {vuln.get('fix_version', 'No fix available')}

"""
        
        return report
    
    def run_full_scan(self):
        """Run complete security scan"""
        print("Starting comprehensive security scan...")
        
        self.scan_python_dependencies()
        self.scan_docker_images()
        self.scan_infrastructure()
        
        # Save results
        with open('security_scan_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate report
        report = self.generate_report()
        with open('security_scan_report.md', 'w') as f:
            f.write(report)
        
        print(f"Scan complete. Found {len(self.results['vulnerabilities'])} issues.")
        print(f"Critical: {self.results['summary']['critical']}, High: {self.results['summary']['high']}")
        
        # Exit with error code if critical or high vulnerabilities found
        if self.results['summary']['critical'] > 0 or self.results['summary']['high'] > 0:
            sys.exit(1)

if __name__ == '__main__':
    scanner = SecurityScanner()
    scanner.run_full_scan()