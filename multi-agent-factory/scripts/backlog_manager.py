#!/usr/bin/env python3
"""
Backlog Management Tool for Multi-Agent Factory Project

This script provides utilities for managing the project backlog including:
- Parsing and validating backlog items
- Generating reports and metrics
- Tracking progress and updates
- Automating backlog maintenance tasks

Usage:
    python backlog_manager.py --help
    python backlog_manager.py validate
    python backlog_manager.py report --format json
    python backlog_manager.py update-status CRIT-001 "In Progress"
    python backlog_manager.py metrics --sprint current
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class BacklogItem:
    """Represents a single backlog item with all its properties."""
    id: str
    title: str
    priority: str
    status: str
    effort: int
    sprint: str
    owner: str
    due_date: Optional[str]
    description: str
    requirements: List[str]
    acceptance_criteria: List[str]
    dependencies: List[str]
    risk: str
    category: str  # CRIT, HIGH, MED, LOW


class BacklogParser:
    """Parses the PROJECT_BACKLOG.md file and extracts backlog items."""
    
    def __init__(self, backlog_path: Path):
        self.backlog_path = backlog_path
        self.items: List[BacklogItem] = []
        
    def parse(self) -> List[BacklogItem]:
        """Parse the backlog markdown file and return list of items."""
        if not self.backlog_path.exists():
            raise FileNotFoundError(f"Backlog file not found: {self.backlog_path}")
            
        content = self.backlog_path.read_text(encoding='utf-8')
        self.items = self._extract_items(content)
        return self.items
    
    def _extract_items(self, content: str) -> List[BacklogItem]:
        """Extract backlog items from markdown content."""
        items = []
        
        # Split content by priority sections
        sections = {
            'CRIT': self._extract_section(content, r'## 🔥 Critical Priority.*?(?=## 🔴|## 🟡|## 🟢|\Z)', 'CRIT'),
            'HIGH': self._extract_section(content, r'## 🔴 High Priority.*?(?=## 🔥|## 🟡|## 🟢|\Z)', 'HIGH'),
            'MED': self._extract_section(content, r'## 🟡 Medium Priority.*?(?=## 🔥|## 🔴|## 🟢|\Z)', 'MED'),
            'LOW': self._extract_section(content, r'## 🟢 Low Priority.*?(?=## 🔥|## 🔴|## 🟡|\Z)', 'LOW')
        }
        
        for category, section_content in sections.items():
            if section_content:
                items.extend(self._parse_section_items(section_content, category))
                
        return items
    
    def _extract_section(self, content: str, pattern: str, category: str) -> Optional[str]:
        """Extract a specific priority section from content."""
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        return match.group(0) if match else None
    
    def _parse_section_items(self, section_content: str, category: str) -> List[BacklogItem]:
        """Parse individual items from a priority section."""
        items = []
        
        # Updated pattern to match the actual format in PROJECT_BACKLOG.md
        # Looking for: ### ITEM-ID: Title
        # **Status**: ... | **Effort**: ... | **Sprint**: ...
        # **Owner**: ... | **Due**: ...
        item_pattern = r'### ([A-Z]+-\d+): (.+?)\n\*\*Status\*\*: (.+?) \| \*\*Effort\*\*: (\d+) points \| \*\*Sprint\*\*: (.+?)\s*\n\*\*Owner\*\*: (.+?) \| \*\*Due\*\*: (.+?)\n\n\*\*Description\*\*: (.+?)\n\n\*\*Requirements\*\*:(.*?)\n\n\*\*Acceptance Criteria\*\*:(.*?)\n\n\*\*Dependencies\*\*: (.+?)\n\*\*Risk\*\*: (.+?)(?=\n\n---|\n\n### |\Z)'
        
        matches = re.finditer(item_pattern, section_content, re.DOTALL)
        
        for match in matches:
            try:
                item_id = match.group(1)
                title = match.group(2).strip()
                status = match.group(3).strip()
                effort = int(match.group(4))
                sprint = match.group(5).strip()
                owner = match.group(6).strip()
                due_date = match.group(7).strip()
                description = match.group(8).strip()
                requirements_text = match.group(9).strip()
                criteria_text = match.group(10).strip()
                dependencies = match.group(11).strip()
                risk = match.group(12).strip()
                
                # Parse requirements list
                requirements = self._parse_list_items(requirements_text)
                
                # Parse acceptance criteria
                acceptance_criteria = self._parse_checklist_items(criteria_text)
                
                item = BacklogItem(
                    id=item_id,
                    title=title,
                    priority=category,
                    status=status,
                    effort=effort,
                    sprint=sprint,
                    owner=owner,
                    due_date=due_date if due_date not in ['TBD', 'None'] else None,
                    description=description,
                    requirements=requirements,
                    acceptance_criteria=acceptance_criteria,
                    dependencies=[dep.strip() for dep in dependencies.split(',') if dep.strip()],
                    risk=risk,
                    category=category
                )
                
                items.append(item)
            except Exception as e:
                print(f"Warning: Failed to parse item {match.group(1) if match.lastindex >= 1 else 'unknown'}: {e}")
                continue
            
        return items
    
    def _parse_list_items(self, text: str) -> List[str]:
        """Parse bullet point list items."""
        items = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                items.append(line[2:].strip())
        return items
    
    def _parse_checklist_items(self, text: str) -> List[str]:
        """Parse checklist items (- [ ] format)."""
        items = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('- [ ]') or line.startswith('- [x]'):
                items.append(line[5:].strip())
        return items


class BacklogAnalyzer:
    """Analyzes backlog items and generates metrics and reports."""
    
    def __init__(self, items: List[BacklogItem]):
        self.items = items
    
    def get_summary_stats(self) -> Dict:
        """Get high-level summary statistics."""
        total_items = len(self.items)
        
        priority_counts = {
            'CRIT': len([i for i in self.items if i.category == 'CRIT']),
            'HIGH': len([i for i in self.items if i.category == 'HIGH']),
            'MED': len([i for i in self.items if i.category == 'MED']),
            'LOW': len([i for i in self.items if i.category == 'LOW'])
        }
        
        status_counts = {}
        for item in self.items:
            status = item.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total_effort = sum(item.effort for item in self.items)
        
        sprint_ready = len([i for i in self.items if i.sprint in ['Current', 'Next']])
        
        return {
            'total_items': total_items,
            'priority_breakdown': priority_counts,
            'status_breakdown': status_counts,
            'total_effort_points': total_effort,
            'sprint_ready_items': sprint_ready,
            'average_effort': round(total_effort / total_items, 1) if total_items > 0 else 0
        }
    
    def get_overdue_items(self) -> List[BacklogItem]:
        """Get items that are past their due date."""
        overdue = []
        today = datetime.now().date()
        
        for item in self.items:
            if item.due_date and item.status not in ['Done', 'Completed']:
                try:
                    due_date = datetime.strptime(item.due_date, '%Y-%m-%d').date()
                    if due_date < today:
                        overdue.append(item)
                except ValueError:
                    # Skip items with invalid date formats
                    continue
                    
        return overdue
    
    def get_blocked_items(self) -> List[BacklogItem]:
        """Get items that are currently blocked."""
        return [item for item in self.items if item.status.lower() == 'blocked']
    
    def get_high_risk_items(self) -> List[BacklogItem]:
        """Get items marked as high risk."""
        return [item for item in self.items if 'high' in item.risk.lower()]
    
    def get_sprint_items(self, sprint: str) -> List[BacklogItem]:
        """Get items for a specific sprint."""
        return [item for item in self.items if item.sprint.lower() == sprint.lower()]
    
    def get_owner_workload(self) -> Dict[str, Dict]:
        """Get workload breakdown by owner."""
        workload = {}
        
        for item in self.items:
            owner = item.owner
            if owner not in workload:
                workload[owner] = {
                    'total_items': 0,
                    'total_effort': 0,
                    'by_priority': {'CRIT': 0, 'HIGH': 0, 'MED': 0, 'LOW': 0},
                    'by_status': {}
                }
            
            workload[owner]['total_items'] += 1
            workload[owner]['total_effort'] += item.effort
            workload[owner]['by_priority'][item.category] += 1
            
            status = item.status
            workload[owner]['by_status'][status] = workload[owner]['by_status'].get(status, 0) + 1
        
        return workload


class BacklogReporter:
    """Generates various reports from backlog data."""
    
    def __init__(self, analyzer: BacklogAnalyzer):
        self.analyzer = analyzer
    
    def generate_summary_report(self, format_type: str = 'text') -> str:
        """Generate a summary report in specified format."""
        stats = self.analyzer.get_summary_stats()
        overdue = self.analyzer.get_overdue_items()
        blocked = self.analyzer.get_blocked_items()
        high_risk = self.analyzer.get_high_risk_items()
        
        if format_type.lower() == 'json':
            return json.dumps({
                'summary_stats': stats,
                'overdue_items': [asdict(item) for item in overdue],
                'blocked_items': [asdict(item) for item in blocked],
                'high_risk_items': [asdict(item) for item in high_risk],
                'generated_at': datetime.now().isoformat()
            }, indent=2)
        
        # Text format
        report = []
        report.append("# Backlog Summary Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("## Overview")
        report.append(f"Total Items: {stats['total_items']}")
        report.append(f"Total Effort: {stats['total_effort_points']} points")
        report.append(f"Average Effort: {stats['average_effort']} points")
        report.append(f"Sprint Ready: {stats['sprint_ready_items']} items")
        report.append("")
        
        report.append("## Priority Breakdown")
        for priority, count in stats['priority_breakdown'].items():
            report.append(f"{priority}: {count} items")
        report.append("")
        
        report.append("## Status Breakdown")
        for status, count in stats['status_breakdown'].items():
            report.append(f"{status}: {count} items")
        report.append("")
        
        if overdue:
            report.append(f"## ⚠️ Overdue Items ({len(overdue)})")
            for item in overdue:
                report.append(f"- {item.id}: {item.title} (Due: {item.due_date})")
            report.append("")
        
        if blocked:
            report.append(f"## 🚫 Blocked Items ({len(blocked)})")
            for item in blocked:
                report.append(f"- {item.id}: {item.title} (Owner: {item.owner})")
            report.append("")
        
        if high_risk:
            report.append(f"## ⚡ High Risk Items ({len(high_risk)})")
            for item in high_risk:
                report.append(f"- {item.id}: {item.title} (Risk: {item.risk})")
            report.append("")
        
        return "\n".join(report)
    
    def generate_sprint_report(self, sprint: str, format_type: str = 'text') -> str:
        """Generate a report for a specific sprint."""
        sprint_items = self.analyzer.get_sprint_items(sprint)
        
        if format_type.lower() == 'json':
            return json.dumps({
                'sprint': sprint,
                'items': [asdict(item) for item in sprint_items],
                'total_items': len(sprint_items),
                'total_effort': sum(item.effort for item in sprint_items),
                'generated_at': datetime.now().isoformat()
            }, indent=2)
        
        # Text format
        report = []
        report.append(f"# Sprint Report: {sprint}")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        total_effort = sum(item.effort for item in sprint_items)
        report.append(f"Total Items: {len(sprint_items)}")
        report.append(f"Total Effort: {total_effort} points")
        report.append("")
        
        if sprint_items:
            report.append("## Items")
            for item in sorted(sprint_items, key=lambda x: (x.category, x.id)):
                report.append(f"### {item.id}: {item.title}")
                report.append(f"Priority: {item.category} | Status: {item.status} | Effort: {item.effort} points")
                report.append(f"Owner: {item.owner} | Due: {item.due_date or 'TBD'}")
                report.append(f"Risk: {item.risk}")
                report.append("")
        else:
            report.append("No items found for this sprint.")
        
        return "\n".join(report)
    
    def generate_owner_report(self, format_type: str = 'text') -> str:
        """Generate a workload report by owner."""
        workload = self.analyzer.get_owner_workload()
        
        if format_type.lower() == 'json':
            return json.dumps({
                'workload_by_owner': workload,
                'generated_at': datetime.now().isoformat()
            }, indent=2)
        
        # Text format
        report = []
        report.append("# Workload Report by Owner")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for owner, data in sorted(workload.items()):
            report.append(f"## {owner}")
            report.append(f"Total Items: {data['total_items']}")
            report.append(f"Total Effort: {data['total_effort']} points")
            report.append("")
            
            report.append("Priority Breakdown:")
            for priority, count in data['by_priority'].items():
                if count > 0:
                    report.append(f"  {priority}: {count} items")
            report.append("")
            
            report.append("Status Breakdown:")
            for status, count in data['by_status'].items():
                report.append(f"  {status}: {count} items")
            report.append("")
        
        return "\n".join(report)


def main():
    """Main CLI interface for backlog management."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Factory Backlog Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backlog_manager.py validate
  python backlog_manager.py report --format json
  python backlog_manager.py sprint-report current
  python backlog_manager.py owner-report --format text
  python backlog_manager.py metrics
        """
    )
    
    parser.add_argument(
        '--backlog-file',
        type=Path,
        default=Path('PROJECT_BACKLOG.md'),
        help='Path to the backlog markdown file'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate backlog file format')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate summary report')
    report_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    # Sprint report command
    sprint_parser = subparsers.add_parser('sprint-report', help='Generate sprint report')
    sprint_parser.add_argument('sprint', help='Sprint name (e.g., current, next, backlog)')
    sprint_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    # Owner report command
    owner_parser = subparsers.add_parser('owner-report', help='Generate owner workload report')
    owner_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    # Metrics command
    metrics_parser = subparsers.add_parser('metrics', help='Show backlog metrics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Parse backlog file
        parser_obj = BacklogParser(args.backlog_file)
        items = parser_obj.parse()
        analyzer = BacklogAnalyzer(items)
        reporter = BacklogReporter(analyzer)
        
        if args.command == 'validate':
            print(f"✅ Successfully parsed {len(items)} backlog items from {args.backlog_file}")
            
            # Check for common issues
            issues = []
            
            # Check for duplicate IDs
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                issues.append("Duplicate item IDs found")
            
            # Check for missing due dates on critical items
            critical_no_due = [item for item in items if item.category == 'CRIT' and not item.due_date]
            if critical_no_due:
                issues.append(f"{len(critical_no_due)} critical items missing due dates")
            
            # Check for high effort items without breakdown
            high_effort = [item for item in items if item.effort > 21]
            if high_effort:
                issues.append(f"{len(high_effort)} items with >21 points (consider breaking down)")
            
            if issues:
                print("\n⚠️ Issues found:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("\n✅ No issues found")
        
        elif args.command == 'report':
            print(reporter.generate_summary_report(args.format))
        
        elif args.command == 'sprint-report':
            print(reporter.generate_sprint_report(args.sprint, args.format))
        
        elif args.command == 'owner-report':
            print(reporter.generate_owner_report(args.format))
        
        elif args.command == 'metrics':
            stats = analyzer.get_summary_stats()
            print(json.dumps(stats, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())