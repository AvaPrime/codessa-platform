# Multi-Agent Factory Project Rules

## Project Context
This is a multi-agent system project focusing on AI agent orchestration and management.

## Code Review Focus Areas

### Security Priorities
- API key handling and storage
- Agent permission boundaries
- Inter-agent communication security
- Data validation for agent inputs/outputs
- Authentication and authorization flows

### Performance Priorities
- Agent memory usage optimization
- Concurrent agent execution efficiency
- Resource cleanup and management
- API rate limiting compliance
- Database query optimization

### Architecture Patterns
- Follow dependency injection patterns
- Maintain clear agent interfaces
- Use factory patterns for agent creation
- Implement proper error boundaries
- Ensure agent isolation

## Coding Standards

### Python Specific
- Use type hints for all function signatures
- Follow PEP 8 style guidelines
- Use dataclasses or Pydantic models for data structures
- Implement proper logging for agent activities
- Use async/await for I/O operations

### Testing Requirements
- Unit tests for individual agent functions
- Integration tests for agent interactions
- Mock external API calls in tests
- Test error handling and edge cases
- Performance tests for resource usage

### Documentation Standards
- Document agent capabilities and limitations
- Include usage examples for each agent
- Maintain API documentation
- Document configuration options
- Keep README files updated

## Agent Development Guidelines

### Agent Design Principles
- Single responsibility per agent
- Clear input/output contracts
- Graceful error handling
- Resource usage monitoring
- Configurable behavior

### Inter-Agent Communication
- Use structured message formats
- Implement proper timeouts
- Handle agent failures gracefully
- Log all agent interactions
- Validate message schemas

### Resource Management
- Monitor memory usage per agent
- Implement connection pooling
- Use caching strategically
- Clean up resources on shutdown
- Implement circuit breakers for external services

## Review Checklist
When reviewing code, always check:
- [ ] Agent permissions are properly scoped
- [ ] Error handling is comprehensive
- [ ] Resources are properly cleaned up
- [ ] Tests cover the happy path and error cases
- [ ] Documentation is updated
- [ ] Performance impact is considered
- [ ] Security implications are evaluated