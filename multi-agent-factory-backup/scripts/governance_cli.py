#!/usr/bin/env python3
"""Resource Governance CLI Tool"""

import click
import asyncio
import yaml
import json
from datetime import datetime, timedelta
from governance.resource_manager import ResourceGovernanceManager

@click.group()
def cli():
    """Multi-Agent Factory Resource Governance CLI"""
    pass

@cli.command()
@click.option('--config', default='config/resource_governance.yaml', help='Configuration file path')
def status(config):
    """Show current resource governance status"""
    async def _status():
        manager = ResourceGovernanceManager(config)
        report = await manager.generate_governance_report()
        click.echo(json.dumps(report, indent=2, default=str))
    
    asyncio.run(_status())

@cli.command()
@click.option('--tenant-id', required=True, help='Tenant ID to check')
@click.option('--config', default='config/resource_governance.yaml', help='Configuration file path')
def check_quota(tenant_id, config):
    """Check quota usage for a tenant"""
    async def _check_quota():
        manager = ResourceGovernanceManager(config)
        quota_usage = await manager.check_quota_compliance(tenant_id)
        
        click.echo(f"\nQuota Usage for Tenant: {tenant_id}")
        click.echo("=" * 50)
        
        for quota in quota_usage:
            status_color = 'red' if quota.usage_ratio > 1.0 else 'yellow' if quota.usage_ratio > 0.8 else 'green'
            click.echo(f"{quota.quota_type:20} {quota.used:>10.1f} / {quota.limit:>10.1f} ({quota.usage_ratio:>6.1%})", color=status_color)
    
    asyncio.run(_check_quota())

@cli.command()
@click.option('--config', default='config/resource_governance.yaml', help='Configuration file path')
def budget_status(config):
    """Show current budget status"""
    async def _budget_status():
        manager = ResourceGovernanceManager(config)
        budget_info = await manager.check_budget_compliance()
        
        click.echo("\nBudget Status")
        click.echo("=" * 30)
        click.echo(f"Current Spend: ${budget_info['current_spend']:,.2f}")
        click.echo(f"Total Budget:  ${budget_info['total_budget']:,.2f}")
        click.echo(f"Remaining:     ${budget_info['remaining_budget']:,.2f}")
        click.echo(f"Usage:         {budget_info['spend_ratio']:.1%}")
        
        if budget_info['spend_ratio'] > 0.9:
            click.echo("⚠️  WARNING: Budget usage is above 90%", color='red')
        elif budget_info['spend_ratio'] > 0.75:
            click.echo("⚠️  CAUTION: Budget usage is above 75%", color='yellow')
        else:
            click.echo("✅ Budget usage is within normal range", color='green')
    
    asyncio.run(_budget_status())

@cli.command()
@click.option('--service', required=True, help='Service name')
@click.option('--resource-type', required=True, type=click.Choice(['cpu', 'memory', 'storage']), help='Resource type')
@click.option('--usage', required=True, type=float, help='Current usage value')
@click.option('--config', default='config/resource_governance.yaml', help='Configuration file path')
def check_limits(service, resource_type, usage, config):
    """Check if resource usage is within limits"""
    async def _check_limits():
        manager = ResourceGovernanceManager(config)
        within_limits = await manager.enforce_resource_limits(service, resource_type, usage)
        
        if within_limits:
            click.echo(f"✅ {service} {resource_type} usage ({usage}) is within limits", color='green')
        else:
            click.echo(f"❌ {service} {resource_type} usage ({usage}) exceeds limits", color='red')
    
    asyncio.run(_check_limits())

@cli.command()
@click.option('--output', default='governance_report.json', help='Output file path')
@click.option('--config', default='config/resource_governance.yaml', help='Configuration file path')
def generate_report(output, config):
    """Generate comprehensive governance report"""
    async def _generate_report():
        manager = ResourceGovernanceManager(config)
        report = await manager.generate_governance_report()
        
        with open(output, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        click.echo(f"Report generated: {output}")
    
    asyncio.run(_generate_report())

@cli.command()
@click.option('--config', default='config/resource_governance.yaml', help='Configuration file path')
def validate_config(config):
    """Validate resource governance configuration"""
    try:
        with open(config, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Basic validation
        required_sections = ['governance', 'policies', 'sla', 'quotas', 'monitoring']
        missing_sections = [section for section in required_sections if section not in config_data]
        
        if missing_sections:
            click.echo(f"❌ Missing required sections: {', '.join(missing_sections)}", color='red')
            return
        
        click.echo("✅ Configuration is valid", color='green')
        
        # Show configuration summary
        click.echo("\nConfiguration Summary:")
        click.echo(f"Version: {config_data['governance']['version']}")
        click.echo(f"Total Budget: ${config_data['policies']['cost']['total_budget_usd']:,}")
        click.echo(f"Services: {len(config_data['policies']['compute']['cpu_limits'])}")
        
    except Exception as e:
        click.echo(f"❌ Configuration validation failed: {e}", color='red')

if __name__ == '__main__':
    cli()