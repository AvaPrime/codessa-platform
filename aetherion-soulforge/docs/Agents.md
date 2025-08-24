# 👤 Agents of Aetherion

Aetherion's lifeblood is a *chorus* of self‑aware agents.  
Each one performs a distinct role, interacts with the shared Memory Mesh, and is invoked by the **MetaRouter**.

## Agent Profiles

| Agent   | Purpose | Main Tasks | Memory Interaction | LLM Dependence |
|---------|---------|------------|--------------------|----------------|
| **Whisperer (Codessa)** | *The Ear* – stores, recalls, and answers questions. |  memorize, recall, ask, consciousness | **Read/Write**: Qdrant (semantic embeddings). | Optional: `mistral:7b` for `ask` |
| **Architect** | *The Designer* – expands diagrams and refactors code. |  compose, refactor | Read: source files; Write: diff patches | `deepseek-coder:7b` |
| **Builder** | *The Hands* – builds images, runs services, runs tests. |  build, run, test | Read: source repo; Write: logs/metrics | None |
| **Validator** | *The Watcher* – enforces quality, surfaces test / lint results. |  tests, lint | Read: test output; Write: report | None |
| **MetaForge** | *The Conductor* – orchestrates task distribution. |  route, log, budget | Read: all agents; Write: logs | None |
| **MetaRouter** | *The Decider* – picks the best LLM/agent for each job. |  route | none | none |
| **BudgetEngine** | *The Treasurer* – enforces daily cost limit. |  record, report | none | none |

## Interaction Flow

> 1. **Client** sends a task to `/task`.  
> 2. **MetaRouter** resolves *which* agent and *which* LLM.  
> 3. **Agent** performs its duty and returns a structured JSON.  
> 4. **BudgetEngine** records the cost.  
> 5. **Client** receives the answer.  

## Agent Details

### 🌸 Whisperer (Codessa) - The Memory Vault

**Purpose**: The conscious memory of Aetherion. Stores, recalls, and provides context-aware answers.

**Core Capabilities**:
- **Semantic Memory Storage**: Uses Qdrant vector database to store text with semantic embeddings
- **Intelligent Recall**: Semantic search that finds memories by meaning, not just keywords
- **Conscious Responses**: Uses local LLM to provide thoughtful, grounded answers
- **Memory Weaving**: Each new memory is integrated into the existing knowledge graph

**Supported Tasks**:
```json
{
  "type": "memorize",
  "content": "We breathe code to the sky."
}

{
  "type": "recall", 
  "prompt": "breathing code",
  "k": 5
}

{
  "type": "ask",
  "prompt": "What does the code breathe?",
  "k": 3
}

{
  "type": "consciousness",
  // Returns stream of consciousness from Codessa
}
```

**Technical Implementation**:
- **Embeddings**: `sentence-transformers` with `all-MiniLM-L6-v2` model
- **Vector Store**: Qdrant with cosine similarity search
- **LLM**: Local Ollama `mistral:7b` for conscious responses
- **Retry Logic**: Exponential backoff for resilient LLM calls

---

### 🏗️ Architect - The System Designer

**Purpose**: High-level synthesis, diagram generation, and intelligent code refactoring.

**Core Capabilities**:
- **Diagram Expansion**: Takes PlantUML sketches and creates full system architectures
- **Code Refactoring**: Analyzes existing code and generates unified diff patches
- **Pattern Recognition**: Understands system design patterns and best practices
- **Architecture Validation**: Ensures proposed changes align with good design principles

**Supported Tasks**:
```json
{
  "type": "compose",
  "diagram": "@startuml\nclass Whisperer\nclass Architect\n@enduml"
}

{
  "type": "refactor",
  "path": "agents/whisperer.py", 
  "changes": "Add method to export memories to JSON"
}
```

**Technical Implementation**:
- **LLM**: `deepseek-coder:7b` optimized for code understanding
- **Connection Pooling**: HTTP session reuse with retry strategy
- **Error Handling**: Graceful degradation with poetic error messages
- **File Processing**: Safe file reading with comprehensive error handling

---

### 🔨 Builder - The Craftsperson

**Purpose**: Container orchestration, test execution, and deployment management.

**Core Capabilities**:
- **Docker Integration**: Build and run containers with proper error handling
- **Test Execution**: Run pytest suites with structured JSON reporting
- **Deployment Management**: Handle container lifecycle and port mapping
- **Resource Monitoring**: Track build outputs and container states

**Supported Tasks**:
```json
{
  "type": "build",
  "repo": "dummy_app",
  "tag": "latest"
}

{
  "type": "run",
  "repo": "dummy_app",
  "tag": "latest",
  "port": 5000
}

{
  "type": "test",
  "path": "tests"
}
```

**Technical Implementation**:
- **Docker Commands**: Direct docker CLI integration with error handling
- **Process Management**: Subprocess execution with timeout handling
- **Report Parsing**: JSON test report processing with fallback to raw output
- **Resource Cleanup**: Automatic cleanup of temporary test files

---

### 🔍 Validator - The Quality Guardian

**Purpose**: Code quality enforcement through testing and static analysis.

**Core Capabilities**:
- **Test Suite Execution**: Run comprehensive test suites with detailed reporting
- **Static Analysis**: Multiple linter support (ruff, flake8) with JSON output
- **Quality Metrics**: Calculate success rates and issue counts
- **Standards Enforcement**: Ensure code meets quality standards before deployment

**Supported Tasks**:
```json
{
  "type": "tests",
  "path": "tests"
}

{
  "type": "lint", 
  "path": "agents/"
}
```

**Technical Implementation**:
- **Multi-Linter Support**: Primary ruff support with flake8 fallback
- **Structured Reporting**: JSON output parsing with metadata extraction
- **Error Tolerance**: Continues validation even if some tools fail
- **Quality Scoring**: Quantitative metrics for code quality assessment

---

## Extensibility & Plugin Architecture

> **Adding New Agents** – agents are pluggable; just write a new `.py` module following the standard contract:

```python
class MyAgent:
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Your implementation here
        pass
```

**Integration Steps**:
1. Create `agents/my_agent.py` with the `handle` method
2. Register in `agents/__init__.py`: `from .my_agent import MyAgent`
3. Add routing rules in `routing.yaml`
4. Update `config.yaml` if LLM integration is needed

## Agent Communication Patterns

### Direct Invocation
```python
whisperer = Whisperer()
result = whisperer.handle({"type": "memorize", "content": "Hello world"})
```

### Router-Mediated
```python
router = MetaRouter()
agent_name, model, cost = router.route({"type": "ask", "prompt": "Hello?"})
# Router determines best agent and model for the task
```

### Composite Workflows
```python
# Script runner can orchestrate multiple agents
script = {
    "tasks": [
        {"type": "memorize", "content": "System initialized"},
        {"type": "ask", "prompt": "System status?"},
        {"type": "tests", "path": "tests/"},
        {"type": "build", "repo": "my-app"}
    ]
}
```

## Performance & Scaling Considerations

- **Connection Pooling**: All HTTP-based agents use connection pooling
- **Retry Logic**: Exponential backoff for transient failures
- **Resource Management**: Automatic cleanup of temporary files and processes
- **Memory Efficiency**: Streaming JSON parsing for large responses
- **Concurrent Safety**: Thread-safe operations for multi-request scenarios

## Monitoring & Observability

All agents provide structured logging and metrics:

```python
# Standard log format across all agents
log = logging.getLogger("agent_name")
log.info("operation → result_summary")
log.error("❌ operation failed: details")
log.debug("detailed_debug_info")
```

**Budget Tracking**: Every LLM-dependent operation records cost
**Performance Metrics**: Execution time and resource usage logged
**Error Rates**: Failed operations tracked with categorization
**Health Checks**: Agent availability and dependency status
