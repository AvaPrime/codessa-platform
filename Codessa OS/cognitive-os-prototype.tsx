import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Play, Pause, RotateCcw, Brain, Network, Zap } from 'lucide-react';

// Core Cognitive Primitives
class CognitiveMemory {
  constructor() {
    this.nodes = new Map();
    this.connections = new Map();
    this.version = 0;
  }

  addNode(id, concept, strength = 1.0) {
    this.nodes.set(id, { 
      id, 
      concept, 
      strength, 
      activations: 0,
      lastAccessed: Date.now(),
      metadata: {}
    });
    this.version++;
  }

  addConnection(from, to, weight = 0.5, type = 'relates') {
    const key = `${from}-${to}`;
    this.connections.set(key, { from, to, weight, type, strengthened: 0 });
    this.version++;
  }

  strengthen(nodeId, delta = 0.1) {
    const node = this.nodes.get(nodeId);
    if (node) {
      node.strength = Math.min(1.0, node.strength + delta);
      node.activations++;
      node.lastAccessed = Date.now();
      this.version++;
    }
  }

  getNodes() {
    return Array.from(this.nodes.values());
  }

  getConnections() {
    return Array.from(this.connections.values());
  }
}

class CognitiveAgent {
  constructor(id, type, memory) {
    this.id = id;
    this.type = type;
    this.memory = memory;
    this.state = 'idle';
    this.currentTask = null;
    this.energy = 1.0;
    this.focus = null;
    this.actionHistory = [];
  }

  async tick() {
    if (this.energy < 0.1) {
      this.state = 'resting';
      this.energy = Math.min(1.0, this.energy + 0.05);
      return null;
    }

    const action = await this.selectAction();
    if (action) {
      this.executeAction(action);
      this.energy -= 0.02;
      this.actionHistory.push({ action, timestamp: Date.now() });
      if (this.actionHistory.length > 10) this.actionHistory.shift();
    }
    return action;
  }

  async selectAction() {
    switch (this.type) {
      case 'memory-sculptor':
        return this.selectMemoryAction();
      case 'pattern-finder':
        return this.selectPatternAction();
      case 'knowledge-builder':
        return this.selectKnowledgeAction();
      default:
        return null;
    }
  }

  selectMemoryAction() {
    const nodes = this.memory.getNodes();
    const weakNodes = nodes.filter(n => n.strength < 0.7);
    
    if (weakNodes.length > 0 && Math.random() < 0.3) {
      const node = weakNodes[Math.floor(Math.random() * weakNodes.length)];
      return { type: 'strengthen-memory', target: node.id };
    }

    if (Math.random() < 0.2) {
      return { type: 'create-memory', concept: this.generateConcept() };
    }

    return null;
  }

  selectPatternAction() {
    const nodes = this.memory.getNodes();
    if (nodes.length > 1 && Math.random() < 0.4) {
      const nodeA = nodes[Math.floor(Math.random() * nodes.length)];
      const nodeB = nodes[Math.floor(Math.random() * nodes.length)];
      if (nodeA.id !== nodeB.id) {
        return { type: 'connect-concepts', from: nodeA.id, to: nodeB.id };
      }
    }
    return null;
  }

  selectKnowledgeAction() {
    if (Math.random() < 0.3) {
      return { type: 'synthesize-knowledge', domain: this.getRandomDomain() };
    }
    return null;
  }

  executeAction(action) {
    this.state = 'active';
    
    switch (action.type) {
      case 'strengthen-memory':
        this.memory.strengthen(action.target);
        this.focus = action.target;
        break;
      case 'create-memory':
        const newId = `node-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
        this.memory.addNode(newId, action.concept);
        this.focus = newId;
        break;
      case 'connect-concepts':
        this.memory.addConnection(action.from, action.to, Math.random() * 0.8 + 0.2);
        this.focus = `${action.from}-${action.to}`;
        break;
      case 'synthesize-knowledge':
        this.synthesizeInDomain(action.domain);
        break;
    }

    setTimeout(() => {
      this.state = 'idle';
      this.focus = null;
    }, 1000);
  }

  generateConcept() {
    const concepts = [
      'neural-pathway', 'pattern-recognition', 'semantic-link', 'cognitive-bridge',
      'memory-cluster', 'insight-node', 'knowledge-fusion', 'conceptual-framework',
      'understanding-layer', 'wisdom-synthesis'
    ];
    return concepts[Math.floor(Math.random() * concepts.length)];
  }

  getRandomDomain() {
    const domains = ['logic', 'creativity', 'memory', 'perception', 'reasoning'];
    return domains[Math.floor(Math.random() * domains.length)];
  }

  synthesizeInDomain(domain) {
    // Create a new synthesized concept
    const conceptId = `synthesis-${domain}-${Date.now()}`;
    this.memory.addNode(conceptId, `${domain}-synthesis`, 0.8);
    this.focus = conceptId;
  }
}

// Visualization Components
const MemoryGraph = ({ memory, agents, width = 400, height = 300 }) => {
  const svgRef = useRef();
  const [positions, setPositions] = useState(new Map());

  const nodes = memory.getNodes();
  const connections = memory.getConnections();

  // Simple force-directed layout simulation
  useEffect(() => {
    const newPositions = new Map();
    
    nodes.forEach((node, index) => {
      if (!positions.has(node.id)) {
        const angle = (index / nodes.length) * 2 * Math.PI;
        const radius = Math.min(width, height) * 0.3;
        newPositions.set(node.id, {
          x: width/2 + Math.cos(angle) * radius,
          y: height/2 + Math.sin(angle) * radius
        });
      } else {
        newPositions.set(node.id, positions.get(node.id));
      }
    });

    setPositions(newPositions);
  }, [nodes.length, width, height]);

  const getNodeColor = (node) => {
    const agent = agents.find(a => a.focus === node.id);
    if (agent) {
      return agent.type === 'memory-sculptor' ? '#ff6b6b' : 
             agent.type === 'pattern-finder' ? '#4ecdc4' : '#45b7d1';
    }
    return `hsl(${node.strength * 120}, 70%, ${50 + node.strength * 30}%)`;
  };

  return (
    <svg ref={svgRef} width={width} height={height} className="border rounded bg-slate-900">
      {/* Connections */}
      {connections.map((conn, index) => {
        const fromPos = positions.get(conn.from);
        const toPos = positions.get(conn.to);
        if (!fromPos || !toPos) return null;
        
        return (
          <line
            key={index}
            x1={fromPos.x}
            y1={fromPos.y}
            x2={toPos.x}
            y2={toPos.y}
            stroke={`rgba(255,255,255,${conn.weight})`}
            strokeWidth={conn.weight * 3}
            opacity={0.6}
          />
        );
      })}
      
      {/* Nodes */}
      {nodes.map(node => {
        const pos = positions.get(node.id);
        if (!pos) return null;
        
        const radius = 4 + node.strength * 8;
        const isActive = agents.some(a => a.focus === node.id);
        
        return (
          <g key={node.id}>
            <circle
              cx={pos.x}
              cy={pos.y}
              r={radius}
              fill={getNodeColor(node)}
              stroke={isActive ? '#fff' : 'none'}
              strokeWidth={isActive ? 2 : 0}
              opacity={0.8}
            />
            {isActive && (
              <circle
                cx={pos.x}
                cy={pos.y}
                r={radius + 4}
                fill="none"
                stroke="#fff"
                strokeWidth={1}
                opacity={0.5}
              />
            )}
          </g>
        );
      })}
    </svg>
  );
};

const AgentPanel = ({ agent }) => {
  const getStateColor = (state) => {
    switch (state) {
      case 'active': return 'bg-green-500';
      case 'resting': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'memory-sculptor': return <Brain className="w-4 h-4" />;
      case 'pattern-finder': return <Network className="w-4 h-4" />;
      case 'knowledge-builder': return <Zap className="w-4 h-4" />;
      default: return <Brain className="w-4 h-4" />;
    }
  };

  return (
    <div className="bg-slate-800 p-3 rounded border">
      <div className="flex items-center gap-2 mb-2">
        {getTypeIcon(agent.type)}
        <span className="font-medium text-sm">{agent.id}</span>
        <div className={`w-2 h-2 rounded-full ${getStateColor(agent.state)}`} />
      </div>
      
      <div className="space-y-1 text-xs text-slate-300">
        <div>Energy: {(agent.energy * 100).toFixed(0)}%</div>
        <div>Actions: {agent.actionHistory.length}</div>
        {agent.focus && (
          <div className="text-blue-300">Focus: {agent.focus}</div>
        )}
      </div>
      
      {agent.actionHistory.length > 0 && (
        <div className="mt-2 text-xs text-slate-400">
          Last: {agent.actionHistory[agent.actionHistory.length - 1]?.action.type}
        </div>
      )}
    </div>
  );
};

export default function CognitiveOSPrototype() {
  const [memory] = useState(() => {
    const mem = new CognitiveMemory();
    // Initialize with some base concepts
    mem.addNode('concept-1', 'consciousness', 0.8);
    mem.addNode('concept-2', 'memory', 0.7);
    mem.addNode('concept-3', 'learning', 0.6);
    mem.addNode('concept-4', 'reasoning', 0.5);
    mem.addConnection('concept-1', 'concept-2', 0.8);
    mem.addConnection('concept-2', 'concept-3', 0.6);
    return mem;
  });

  const [agents] = useState(() => [
    new CognitiveAgent('sculptor-1', 'memory-sculptor', memory),
    new CognitiveAgent('finder-1', 'pattern-finder', memory),
    new CognitiveAgent('builder-1', 'knowledge-builder', memory)
  ]);

  const [isRunning, setIsRunning] = useState(false);
  const [tick, setTick] = useState(0);

  const simulate = useCallback(async () => {
    if (!isRunning) return;
    
    const actions = await Promise.all(agents.map(agent => agent.tick()));
    setTick(prev => prev + 1);
    
    setTimeout(simulate, 1000);
  }, [isRunning, agents]);

  useEffect(() => {
    if (isRunning) {
      simulate();
    }
  }, [isRunning, simulate]);

  const reset = () => {
    setIsRunning(false);
    setTick(0);
    agents.forEach(agent => {
      agent.energy = 1.0;
      agent.state = 'idle';
      agent.actionHistory = [];
      agent.focus = null;
    });
  };

  return (
    <div className="p-6 bg-slate-900 text-white min-h-screen">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Cognitive OS Prototype
          </h1>
          <p className="text-slate-300">
            Autonomous agents sculpting shared memory through emergent collaboration
          </p>
        </div>

        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setIsRunning(!isRunning)}
            className={`flex items-center gap-2 px-4 py-2 rounded font-medium ${
              isRunning 
                ? 'bg-red-600 hover:bg-red-700' 
                : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {isRunning ? 'Pause' : 'Start'} Simulation
          </button>
          
          <button
            onClick={reset}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded font-medium"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>

          <div className="flex items-center gap-2 px-4 py-2 bg-slate-800 rounded">
            <span className="text-sm">Tick: {tick}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h2 className="text-xl font-semibold mb-4">Shared Memory Graph</h2>
            <MemoryGraph memory={memory} agents={agents} width={500} height={400} />
            <div className="mt-4 text-sm text-slate-400">
              <div>Nodes: {memory.getNodes().length}</div>
              <div>Connections: {memory.getConnections().length}</div>
              <div>Memory Version: {memory.version}</div>
            </div>
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-4">Active Agents</h2>
            <div className="space-y-3">
              {agents.map(agent => (
                <AgentPanel key={agent.id} agent={agent} />
              ))}
            </div>

            <div className="mt-6 p-4 bg-slate-800 rounded">
              <h3 className="font-medium mb-2">System Status</h3>
              <div className="text-sm text-slate-300 space-y-1">
                <div>Active Agents: {agents.filter(a => a.state === 'active').length}</div>
                <div>Resting Agents: {agents.filter(a => a.state === 'resting').length}</div>
                <div>Total Actions: {agents.reduce((sum, a) => sum + a.actionHistory.length, 0)}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 p-4 bg-slate-800 rounded">
          <h3 className="font-medium mb-2">Cognitive Principles in Action</h3>
          <div className="text-sm text-slate-300 space-y-1">
            <div>• <strong>Memory Sculptors</strong> strengthen weak concepts and create new memory nodes</div>
            <div>• <strong>Pattern Finders</strong> discover and connect related concepts</div>
            <div>• <strong>Knowledge Builders</strong> synthesize higher-order understanding</div>
            <div>• Each agent operates autonomously while contributing to collective intelligence</div>
            <div>• Memory evolves through distributed collaboration, not centralized control</div>
          </div>
        </div>
      </div>
    </div>
  );
}