# Streamlined Test Matrix

This document describes the streamlined test matrix implementation for the Multi-Agent Factory project, designed to provide fast feedback while maintaining deployment confidence through essential test coverage.

## Overview

The streamlined test matrix focuses on:
- **Critical path validation** - Core functionality that must work
- **Fast execution times** - Total CI time under 15 minutes
- **Essential coverage** - Key areas without redundancy
- **Deployment confidence** - Sufficient validation for production releases

## Test Matrix Structure

### 1. Quick Validation (< 5 minutes)
- **Purpose**: Fast feedback loop for immediate issues
- **Scope**: Code quality, imports, basic sanity
- **Triggers**: All pushes and PRs

```bash
# Local equivalent
make test-critical
```

### 2. Core Test Matrix (< 15 minutes)
Parallel execution of essential test suites:

#### Auth & Security Suite
- **Path**: `tests/unit/test_api_auth.py tests/security/`
- **Markers**: `not slow`
- **Coverage**: Enabled (target >95%)
- **Critical**: Yes
- **Focus**: Authentication, authorization, security validation

#### Core API Suite
- **Path**: `tests/unit/ -k 'not auth'`
- **Markers**: `not slow and not integration`
- **Coverage**: Enabled (target >90%)
- **Critical**: Yes
- **Focus**: Business logic, API endpoints, data validation

#### Agent Workflows Suite
- **Path**: `tests/integration/test_task_workflow.py`
- **Markers**: `integration`
- **Coverage**: Disabled (focus on functionality)
- **Critical**: Yes
- **Focus**: Agent communication, task orchestration

#### System Critical Suite
- **Path**: `tests/system/test_fault_tolerance.py`
- **Markers**: `system and critical`
- **Coverage**: Disabled
- **Critical**: Yes
- **Focus**: Fault tolerance, system resilience

### 3. Edge Cases & Regression (main branch only)
- **Purpose**: Catch edge cases and prevent regressions
- **Execution**: Non-blocking (failures don't block deployment)
- **Scope**: Edge cases, known regression scenarios

### 4. Deployment Readiness Check
- **Purpose**: Final validation before deployment
- **Scope**: Configuration validation, security scan
- **Output**: Deployment confidence signal

## Test Markers

The matrix uses pytest markers for precise test selection:

```python
# Speed-based markers
@pytest.mark.slow          # Tests taking >30 seconds

# Category markers
@pytest.mark.integration   # Integration tests
@pytest.mark.system        # System-level tests
@pytest.mark.security      # Security-focused tests

# Priority markers
@pytest.mark.critical      # Critical path tests
@pytest.mark.edge_case     # Edge case scenarios
@pytest.mark.regression    # Regression prevention
```

## Local Development

### Running the Full Matrix
```bash
# Run complete streamlined matrix
make test-matrix

# Run only critical tests (fastest)
make test-critical

# Run security-focused tests
make test-security

# Validate matrix configuration
make test-validate
```

### Pre-commit Validation
```bash
# Recommended pre-commit sequence
make lint
make test-critical
```

## Coverage Targets

| Component | Target | Rationale |
|-----------|--------|-----------|
| Security modules | >95% | Critical for system security |
| Core API | >90% | Essential business logic |
| Agent workflows | Functional | Focus on integration over coverage |
| System tests | Scenario-based | Validate critical paths |

## Maintenance Guidelines

### Adding New Tests

1. **Identify the appropriate suite**:
   - Unit tests → Core API or Auth & Security
   - Integration tests → Agent Workflows
   - System tests → System Critical

2. **Apply appropriate markers**:
   ```python
   @pytest.mark.critical      # For critical path functionality
   @pytest.mark.security      # For security-related tests
   @pytest.mark.slow          # For tests >30 seconds
   ```

3. **Keep execution time under limits**:
   - Individual tests: <10 seconds
   - Test suites: <10 minutes
   - Total matrix: <15 minutes

### Optimizing Test Performance

1. **Use fixtures efficiently**:
   ```python
   @pytest.fixture(scope="session")
   def expensive_setup():
       # Reuse across test session
   ```

2. **Mock external dependencies**:
   ```python
   @pytest.mark.unit
   def test_api_call(mock_external_service):
       # Fast, isolated test
   ```

3. **Parallelize when possible**:
   ```bash
   pytest -n auto  # Use all CPU cores
   ```

### Removing Tests

1. **Analyze impact**: Ensure critical paths remain covered
2. **Consider alternatives**: Move to extended matrix instead of removal
3. **Update documentation**: Reflect coverage changes
4. **Validate matrix**: Run `make test-validate`

## CI/CD Integration

### GitHub Actions Workflow

The streamlined matrix is implemented in `.github/workflows/ci.yml`:

- **Parallel execution** of test suites
- **Conditional execution** based on branch/event
- **Service dependencies** only when needed
- **Coverage reporting** for critical suites
- **Deployment readiness** validation

### Branch-specific Behavior

| Branch/Event | Test Scope | Coverage | Services |
|--------------|------------|----------|---------|
| PR | Core matrix | Yes | Minimal |
| main push | Core + edge cases | Yes | Full |
| Scheduled | Full matrix | Yes | Full |

## Monitoring and Metrics

### Key Metrics
- **Execution time**: Target <15 minutes total
- **Pass rate**: Target >95%
- **Coverage**: Per-suite targets
- **Flakiness**: <2% flaky test rate

### Alerts
- Matrix execution time >20 minutes
- Critical test failures
- Coverage drops below targets
- High flakiness detected

## Troubleshooting

### Common Issues

1. **Tests timing out**:
   - Check for infinite loops or blocking calls
   - Add appropriate timeouts
   - Consider mocking slow operations

2. **Flaky tests**:
   - Identify race conditions
   - Add proper wait conditions
   - Use deterministic test data

3. **Coverage drops**:
   - Identify uncovered code paths
   - Add targeted tests
   - Review test effectiveness

### Debug Commands

```bash
# Run with verbose output
pytest -v --tb=long

# Run specific suite with debugging
pytest tests/unit/test_api_auth.py -v -s --pdb

# Check test discovery
pytest --collect-only

# Validate markers
pytest --markers
```

## Future Enhancements

1. **Adaptive matrix**: Adjust based on code changes
2. **Predictive testing**: Run tests likely to fail
3. **Performance regression**: Detect performance degradation
4. **Smart parallelization**: Optimize test distribution

## References

- [Test Matrix Configuration](../tests/test_matrix_config.py)
- [Pytest Configuration](../../pyproject.toml)
- [CI Workflow](../../.github/workflows/ci.yml)
- [Testing Strategy](./strategy.md)