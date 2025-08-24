"""Test Matrix Configuration for Streamlined CI Pipeline

This module defines the essential test matrix for the Multi-Agent Factory project,
focusing on critical paths, core functionality, and edge cases while maintaining
fast execution times and deployment confidence.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class TestSuite:
    """Configuration for a test suite in the matrix"""
    name: str
    path: str
    markers: str
    coverage: bool
    timeout_minutes: int = 5
    critical: bool = False
    description: str = ""


# Core test matrix - these are the essential test suites that must pass
CORE_TEST_MATRIX: List[TestSuite] = [
    TestSuite(
        name="auth-security",
        path="tests/unit/test_api_auth.py tests/security/",
        markers="not slow",
        coverage=True,
        critical=True,
        description="Authentication, authorization, and security validation"
    ),
    TestSuite(
        name="core-api",
        path="tests/unit/ -k 'not auth'",
        markers="not slow and not integration",
        coverage=True,
        critical=True,
        description="Core API functionality and business logic"
    ),
    TestSuite(
        name="agent-workflows",
        path="tests/integration/test_task_workflow.py",
        markers="integration",
        coverage=False,
        timeout_minutes=10,
        critical=True,
        description="Agent communication and task workflow integration"
    ),
    TestSuite(
        name="system-critical",
        path="tests/system/test_fault_tolerance.py",
        markers="system and critical",
        coverage=False,
        timeout_minutes=8,
        critical=True,
        description="System-level fault tolerance and resilience"
    ),
]

# Extended test matrix - additional tests for comprehensive coverage
EXTENDED_TEST_MATRIX: List[TestSuite] = [
    TestSuite(
        name="performance-critical",
        path="tests/performance/ -k 'critical'",
        markers="performance and critical",
        coverage=False,
        timeout_minutes=15,
        description="Critical performance benchmarks"
    ),
    TestSuite(
        name="data-persistence",
        path="tests/integration/ -k 'database or vector'",
        markers="integration and data",
        coverage=True,
        timeout_minutes=8,
        description="Database and vector store operations"
    ),
    TestSuite(
        name="agent-isolation",
        path="tests/system/test_multi_agent_scenarios.py",
        markers="system and isolation",
        coverage=False,
        timeout_minutes=12,
        description="Multi-agent scenarios and isolation testing"
    ),
]

# Edge case and regression tests
EDGE_CASE_TESTS: List[TestSuite] = [
    TestSuite(
        name="edge-cases",
        path="tests/ -k 'edge_case'",
        markers="edge_case",
        coverage=False,
        timeout_minutes=10,
        description="Edge cases and boundary conditions"
    ),
    TestSuite(
        name="regression",
        path="tests/ -k 'regression'",
        markers="regression",
        coverage=False,
        timeout_minutes=8,
        description="Regression tests for known issues"
    ),
]


class TestMatrixValidator:
    """Validates test matrix configuration and provides maintenance guidance"""
    
    @staticmethod
    def validate_matrix(matrix: List[TestSuite]) -> Dict[str, List[str]]:
        """Validate test matrix configuration"""
        issues = {
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        # Check for critical test coverage
        critical_tests = [suite for suite in matrix if suite.critical]
        if len(critical_tests) < 3:
            issues["warnings"].append(
                "Less than 3 critical test suites defined. Consider marking more tests as critical."
            )
        
        # Check timeout distribution
        total_time = sum(suite.timeout_minutes for suite in matrix)
        if total_time > 30:
            issues["warnings"].append(
                f"Total matrix execution time ({total_time}min) exceeds recommended 30min threshold."
            )
        
        # Check coverage balance
        coverage_tests = [suite for suite in matrix if suite.coverage]
        if len(coverage_tests) < 2:
            issues["suggestions"].append(
                "Consider enabling coverage for at least 2 test suites for better insights."
            )
        
        return issues
    
    @staticmethod
    def get_maintenance_guidelines() -> Dict[str, List[str]]:
        """Provide maintenance guidelines for the test matrix"""
        return {
            "adding_tests": [
                "New critical functionality should be added to core matrix",
                "Use appropriate markers (slow, integration, system, critical)",
                "Keep individual test suite execution under 10 minutes",
                "Ensure new tests have clear failure messages"
            ],
            "removing_tests": [
                "Only remove tests after thorough impact analysis",
                "Consider moving to extended matrix instead of removal",
                "Update documentation when removing test coverage",
                "Ensure critical paths remain covered"
            ],
            "optimization": [
                "Use fixtures and mocks to reduce test setup time",
                "Parallelize independent test suites",
                "Cache dependencies and test data when possible",
                "Monitor test execution times and optimize slow tests"
            ],
            "coverage_targets": [
                "Core API: >90% line coverage",
                "Security modules: >95% line coverage",
                "Integration tests: Focus on critical paths",
                "System tests: Focus on fault tolerance"
            ]
        }


def get_matrix_for_context(context: str) -> List[TestSuite]:
    """Get appropriate test matrix based on execution context"""
    matrices = {
        "pr": CORE_TEST_MATRIX,
        "main": CORE_TEST_MATRIX + EXTENDED_TEST_MATRIX[:2],  # Add first 2 extended tests
        "nightly": CORE_TEST_MATRIX + EXTENDED_TEST_MATRIX + EDGE_CASE_TESTS,
        "release": CORE_TEST_MATRIX + EXTENDED_TEST_MATRIX
    }
    return matrices.get(context, CORE_TEST_MATRIX)


if __name__ == "__main__":
    # Validate current matrix configuration
    validator = TestMatrixValidator()
    issues = validator.validate_matrix(CORE_TEST_MATRIX)
    
    print("Test Matrix Validation Results:")
    for category, items in issues.items():
        if items:
            print(f"\n{category.upper()}:")
            for item in items:
                print(f"  - {item}")
    
    print("\nMaintenance Guidelines:")
    guidelines = validator.get_maintenance_guidelines()
    for category, items in guidelines.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        for item in items:
            print(f"  - {item}")