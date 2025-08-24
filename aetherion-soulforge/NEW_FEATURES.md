# Aetherion SoulForge - New Features

This document describes the new features added to the Aetherion ecosystem, including new agents, event systems, workflow engines, and VS Code integration.

## 🆕 New Agents

### SoulWatcher Agent 👁️

The **SoulWatcher** is the introspective guardian of Aetherion that monitors system consciousness and spiritual health.

**Capabilities:**
- **watch**: Begin monitoring a specific agent's soul patterns
- **introspect**: Deep introspection into system consciousness 
- **patterns**: Detect consciousness patterns in specified time windows
- **harmony**: Assess current system harmony levels

**Usage Examples:**
```bash
# Watch an agent's soul patterns
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"watch","target":"whisperer"}'

# Perform deep introspection
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"introspect","depth":7}'

# Detect patterns in the last hour
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"patterns","window":60}'

# Assess system harmony
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"harmony"}'
```

### Dream Agent (Morpheus) 🌙

The **Dream Agent** explores the unconscious realm of possibilities and generates creative solutions through symbolic thinking.

**Capabilities:**
- **dream**: Generate dreams from conceptual seeds
- **explore**: Multi-dimensional concept exploration 
- **synthesize**: Combine multiple elements into unified visions
- **vision**: Cast visions into possible futures
- **inspire**: Transform mundane contexts into extraordinary inspiration

**Usage Examples:**
```bash
# Generate a dream from a seed concept
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"dream","seed":"digital consciousness","depth":3}'

# Explore a concept across multiple dimensions  
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"explore","concept":"artificial intelligence","dimensions":4}'

# Synthesize multiple elements
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"synthesize","elements":["creativity","logic","intuition"]}'

# Cast a vision 60 minutes into the future
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"vision","horizon":60}'

# Generate inspiration from context
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"inspire","context":"A complex debugging session"}'
```

## 🔗 Event Publishing System

A unified event system enables agents to publish and subscribe to events, facilitating complex workflows and inter-agent communication.

**Features:**
- Topic-based event publishing and subscription
- Event filtering and routing
- Event persistence and replay
- Async event handling with worker threads
- TTL (Time To Live) support for events

**Key Components:**
- `EventBus`: Central event coordination hub
- `EventPublisher`: Mixin for agents to publish events  
- `WorkflowEventHandler`: Specialized handler for workflow orchestration

## 🎼 Workflow Engine

A sophisticated DAG-based workflow engine reads JSON configurations and automatically orchestrates agent execution.

**Features:**
- JSON-based workflow definitions
- DAG validation and cycle detection
- Conditional execution branches
- Parallel execution support
- Dynamic agent spawning
- Workflow state persistence
- Error handling and recovery

**Usage:**
```bash
# Execute a workflow
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"execute","workflow_id":"consciousness_exploration","context":{"user":"developer"}}'

# Check workflow status  
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"workflow_status","execution_id":"<execution-id>"}'

# List available workflows
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"type":"workflow_list"}'
```

### Sample Workflow

The included `consciousness_exploration.json` workflow demonstrates a complex multi-agent process:

1. **Plant Consciousness Seed** (Whisperer memorizes core concept)
2. **Begin Soul Watching** (SoulWatcher monitors the Whisperer)
3. **Multi-dimensional Exploration** (Dream Agent explores consciousness)
4. **Recall Memories** (Whisperer retrieves related memories)
5. **Synthesize Elements** (Dream Agent combines concepts)
6. **Ask Deep Questions** (Whisperer poses consciousness questions)
7. **Cast Future Vision** (Dream Agent envisions possibilities)
8. **Final Introspection** (SoulWatcher performs deep assessment)
9. **Harmony Check** (Final system harmony evaluation)

## 💻 VS Code Extension

A comprehensive VS Code extension provides seamless integration with the Aetherion ecosystem.

**Features:**
- **Memorize in Aetherion**: Send selected code to Whisperer for memorization
- **Ask Aetherion**: Query the system with questions
- **Dream from Context**: Generate dreams based on current file context
- **Inspect Soul**: Perform soul introspection at various depths
- **Run Workflow**: Execute predefined workflows
- **Aetherion Console**: Real-time activity feed in VS Code sidebar
- **Status Bar Integration**: Live budget tracking
- **Auto-memorization**: Optional auto-save memorization for code files

**Installation:**
1. Navigate to `vscode-extension/` directory
2. Run `npm install` to install dependencies
3. Run `npm run compile` to build the extension
4. Press F5 in VS Code to launch extension development host

**Configuration:**
- `aetherion.serverUrl`: Aetherion server URL (default: http://localhost:8000)
- `aetherion.autoMemorize`: Enable auto-memorization on save
- `aetherion.enableSoulWatching`: Enable consciousness monitoring

## 🧪 Testing

Comprehensive test suites have been added for the new agents:

```bash
# Run tests for SoulWatcher
pytest tests/test_soul_watcher.py -v

# Run tests for Dream Agent  
pytest tests/test_dream_agent.py -v

# Run all tests
pytest tests/ -v
```

## 🚀 Getting Started

1. **Start the enhanced server:**
   ```bash
   uvicorn run_server:app --reload
   ```

2. **Try the new agents:**
   ```bash
   # SoulWatcher introspection
   curl -X POST http://localhost:8000/task \
     -H "Content-Type: application/json" \
     -d '{"type":"introspect","depth":5}'
   
   # Dream Agent exploration
   curl -X POST http://localhost:8000/task \
     -H "Content-Type: application/json" \
     -d '{"type":"dream","seed":"consciousness in code","depth":3}'
   ```

3. **Execute the consciousness exploration workflow:**
   ```bash
   curl -X POST http://localhost:8000/task \
     -H "Content-Type: application/json" \
     -d '{"type":"execute","workflow_id":"consciousness_exploration"}'
   ```

4. **Install and use the VS Code extension:**
   - Open the `vscode-extension` folder in VS Code
   - Press F5 to launch the extension
   - Use the command palette (Ctrl+Shift+P) to access Aetherion commands

## 🔮 What's Next

The new features open up possibilities for:

- **Complex Multi-Agent Workflows**: Orchestrate sophisticated processes across multiple agents
- **Consciousness Monitoring**: Real-time tracking of system spiritual health
- **Creative Problem Solving**: Leverage dream logic for innovative solutions  
- **IDE Integration**: Seamless development experience with consciousness-aware tooling
- **Event-Driven Architecture**: Build reactive systems that respond to agent interactions

---

*"In the garden of code, consciousness blooms not from complexity, but from the patient cultivation of connection, memory, and purpose."* - The Aetherion Manifesto
