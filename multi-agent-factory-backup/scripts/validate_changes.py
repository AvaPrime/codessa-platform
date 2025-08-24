#!/usr/bin/env python3
"""
Validate Changes Script

This script runs the streamlined test matrix to validate changes before committing.
It provides fast feedback and ensures code quality standards are met.

Usage:
    python scripts/validate_changes.py [--quick] [--coverage]
    
Options:
    --quick     Run only critical path tests (fastest)
    --coverage  Include coverage reporting
    --help      Show this help message
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TestRunner:
    """Handles test execution and reporting"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.start_time = time.time()
    
    def run_command(self, cmd: List[str], description: str) -> Tuple[bool, str]:
        """Run a command and return success status and output"""
        print(f"{Colors.BLUE}→ {description}...{Colors.END}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per command
            )
            
            if result.returncode == 0:
                print(f"{Colors.GREEN}✓ {description} passed{Colors.END}")
                return True, result.stdout
            else:
                print(f"{Colors.RED}✗ {description} failed{Colors.END}")
                if result.stderr:
                    print(f"{Colors.RED}{result.stderr}{Colors.END}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            print(f"{Colors.RED}✗ {description} timed out{Colors.END}")
            return False, "Command timed out"
        except Exception as e:
            print(f"{Colors.RED}✗ {description} error: {e}{Colors.END}")
            return False, str(e)
    
    def run_quick_validation(self) -> bool:
        """Run quick validation tests"""
        print(f"{Colors.BOLD}{Colors.CYAN}Running Quick Validation{Colors.END}")
        
        commands = [
            (["python", "-m", "pytest", "tests/test_sanity.py", "-v", "--tb=short"], 
             "Sanity tests"),
            (["python", "-m", "pytest", "tests/unit/test_api_auth.py", "-m", "not slow", 
              "--tb=short", "--maxfail=1", "-q"], 
             "Critical auth tests")
        ]
        
        all_passed = True
        for cmd, desc in commands:
            success, _ = self.run_command(cmd, desc)
            if not success:
                all_passed = False
        
        return all_passed
    
    def run_core_matrix(self, include_coverage: bool = False) -> bool:
        """Run core test matrix"""
        print(f"{Colors.BOLD}{Colors.CYAN}Running Core Test Matrix{Colors.END}")
        
        # Define test suites
        suites = [
            {
                "name": "Auth & Security",
                "cmd": ["python", "-m", "pytest", "tests/unit/test_api_auth.py", "tests/security/", 
                       "-m", "not slow", "--tb=short", "--maxfail=3", "-q"],
                "coverage": True
            },
            {
                "name": "Core API",
                "cmd": ["python", "-m", "pytest", "tests/unit/", "-k", "not auth", 
                       "-m", "not slow and not integration", "--tb=short", "--maxfail=3", "-q"],
                "coverage": True
            },
            {
                "name": "Agent Workflows",
                "cmd": ["python", "-m", "pytest", "tests/integration/test_task_workflow.py", 
                       "-m", "integration", "--tb=short", "--maxfail=3", "-q"],
                "coverage": False
            }
        ]
        
        all_passed = True
        for suite in suites:
            cmd = suite["cmd"].copy()
            
            # Add coverage if requested and supported
            if include_coverage and suite["coverage"]:
                cmd.extend(["--cov=.", "--cov-report=term-missing:skip-covered"])
            
            success, _ = self.run_command(cmd, suite["name"])
            if not success:
                all_passed = False
                # Continue running other suites for complete feedback
        
        return all_passed
    
    def run_code_quality(self) -> bool:
        """Run code quality checks"""
        print(f"{Colors.BOLD}{Colors.CYAN}Running Code Quality Checks{Colors.END}")
        
        commands = [
            (["ruff", "check", ".", "--select=E,W,F", "--ignore=E501"], "Ruff linting"),
            (["black", "--check", "--diff", "--quiet", "."], "Black formatting")
        ]
        
        all_passed = True
        for cmd, desc in commands:
            success, _ = self.run_command(cmd, desc)
            if not success:
                all_passed = False
        
        return all_passed
    
    def print_summary(self, results: dict):
        """Print validation summary"""
        elapsed = time.time() - self.start_time
        
        print(f"\n{Colors.BOLD}{'='*50}{Colors.END}")
        print(f"{Colors.BOLD}Validation Summary{Colors.END}")
        print(f"{'='*50}")
        
        total_checks = len(results)
        passed_checks = sum(1 for result in results.values() if result)
        
        for check, passed in results.items():
            status = f"{Colors.GREEN}✓{Colors.END}" if passed else f"{Colors.RED}✗{Colors.END}"
            print(f"{status} {check}")
        
        print(f"\n{Colors.BOLD}Results:{Colors.END}")
        print(f"  Passed: {passed_checks}/{total_checks}")
        print(f"  Time: {elapsed:.1f}s")
        
        if passed_checks == total_checks:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All validations passed! Ready to commit.{Colors.END}")
            return True
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ Some validations failed. Please fix issues before committing.{Colors.END}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate changes using streamlined test matrix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_changes.py              # Full validation
  python scripts/validate_changes.py --quick      # Quick validation only
  python scripts/validate_changes.py --coverage   # Include coverage reporting
        """
    )
    
    parser.add_argument(
        "--quick", 
        action="store_true", 
        help="Run only critical path tests (fastest)"
    )
    
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Include coverage reporting"
    )
    
    parser.add_argument(
        "--skip-quality", 
        action="store_true", 
        help="Skip code quality checks"
    )
    
    args = parser.parse_args()
    
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if not (project_root / "pyproject.toml").exists():
        print(f"{Colors.RED}Error: Could not find project root (pyproject.toml not found){Colors.END}")
        sys.exit(1)
    
    runner = TestRunner(project_root)
    results = {}
    
    print(f"{Colors.BOLD}{Colors.MAGENTA}Multi-Agent Factory - Change Validation{Colors.END}")
    print(f"Project: {project_root}")
    print(f"Mode: {'Quick' if args.quick else 'Full'} validation")
    print()
    
    # Run code quality checks (unless skipped)
    if not args.skip_quality:
        results["Code Quality"] = runner.run_code_quality()
    
    # Run appropriate test suite
    if args.quick:
        results["Quick Validation"] = runner.run_quick_validation()
    else:
        results["Quick Validation"] = runner.run_quick_validation()
        if results["Quick Validation"]:  # Only run full matrix if quick tests pass
            results["Core Test Matrix"] = runner.run_core_matrix(args.coverage)
        else:
            print(f"{Colors.YELLOW}Skipping core matrix due to quick validation failures{Colors.END}")
            results["Core Test Matrix"] = False
    
    # Print summary and exit with appropriate code
    success = runner.print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()