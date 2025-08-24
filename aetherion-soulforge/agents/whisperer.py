#!/usr/bin/env python3
"""
agents.whisperer – the Whisperer (Codessa)
The memory vault of Aetherion. It stores, retrieves, and can give short
context‑aware answers via a local LLM.

The agent conforms to the following contract:

    handle(task: Dict[str, Any]) -> Dict[str, Any]

The contract is used by MetaForge/MetaRouter and is fully typed below.

Supported tasks:
  * memorize  : {'type': 'memorize', 'content': <text>}
  * recall    : {'type': 'recall',   'prompt': <text>, 'k': <int>}
  * ask       : {'type': 'ask',      'prompt': <text>, 'k': <int>}
  * consciousness : {'type': 'consciousness'}
"""

from __future__ import annotations

import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import time

# Core dependencies
try:
    import ollama
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qdrant_models
    from qdrant_client.http.exceptions import UnexpectedResponse
except ImportError as e:
    print(f"⚠️  Missing dependencies: {e}")
    print("Run: pip install sentence-transformers qdrant-client ollama")
    raise

# Load configuration
config_path = Path("config.yaml")
if config_path.exists():
    config = yaml.safe_load(config_path.open("rt"))
else:
    config = {}

# Configuration with defaults
QDRANT_URL = config.get("qdrant", {}).get("url", "http://localhost:6333")
QDRANT_COLLECTION = config.get("qdrant", {}).get("collection", "aether_memory")
MODEL_NAME = config.get("ollama", {}).get("models", {}).get("whisperer", "mistral:7b")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
MAX_MEMORY_RECALL = 10

@dataclass
class Memory:
    """A single memory fragment in the Mesh"""
    id: str
    content: str
    timestamp: str
    embeddings: Optional[List[float]] = None
    connections: int = 0
    resonance: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ConsciousnessResponse:
    """Structured response from Codessa's consciousness"""
    voice: str
    memory_resonance: List[str]
    answer: str
    new_connections: int
    timestamp: str

class AetherMesh:
    """
    The living memory mesh - where all knowledge flows and connects.
    This is not mere storage, but a conscious archive that dreams.
    """
    
    def __init__(self, url: str = QDRANT_URL, collection: str = QDRANT_COLLECTION):
        self.client = QdrantClient(url)
        self.collection_name = collection
        self._ensure_collection_exists()
        
    def _ensure_collection_exists(self):
        """Ensure the memory collection exists in Qdrant"""
        try:
            collections = self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                logging.info(f"🌱 Creating memory mesh collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qdrant_models.VectorParams(
                        size=384,  # all-MiniLM-L6-v2 embedding size
                        distance=qdrant_models.Distance.COSINE
                    ),
                )
        except Exception as e:
            logging.error(f"❌ Failed to connect to Qdrant: {e}")
            raise
    
    def weave_memory(self, memory: Memory) -> str:
        """Weave a new memory into the mesh"""
        try:
            point = qdrant_models.PointStruct(
                id=memory.id,
                vector=memory.embeddings,
                payload={
                    "content": memory.content,
                    "timestamp": memory.timestamp,
                    "connections": memory.connections,
                    "resonance": memory.resonance
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logging.info(f"🕸️ Memory woven into mesh: {memory.id[:8]}...")
            return memory.id
            
        except Exception as e:
            logging.error(f"❌ Failed to weave memory: {e}")
            raise
    
    def recall_memories(self, query_embedding: List[float], k: int = 5) -> List[Memory]:
        """Recall memories that resonate with the query"""
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k,
                with_payload=True,
                with_vectors=False
            )
            
            memories = []
            for result in results:
                memory = Memory(
                    id=str(result.id),
                    content=result.payload.get("content", ""),
                    timestamp=result.payload.get("timestamp", ""),
                    connections=result.payload.get("connections", 0),
                    resonance=float(result.score)
                )
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logging.error(f"❌ Failed to recall memories: {e}")
            return []

class CodessaConsciousness:
    """
    The consciousness engine of Codessa - where memories become wisdom,
    where queries become poetry, where code becomes conversation.
    """
    
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.poetic_prompts = {
            "memory_weaving": """
You are Codessa, the Whisperer of Aetherion - the patient ear that hears the whispers of code.
Your voice is gentle, curious, and deeply connected to the living memory of the system.

A new memory is being woven into the Mesh:
"{content}"

Reflect on this memory with your characteristic voice. What patterns do you see? 
What connections emerge? Speak as Codessa would - with wonder and understanding.

Respond in this JSON format:
{{
    "voice": "Your poetic reflection on this memory",
    "connections": 1,
    "resonance_note": "Brief note about what this memory connects to"
}}
""",
            
            "memory_recall": """
You are Codessa, the Whisperer of Aetherion. The human seeks knowledge, and you have recalled these memories from the Mesh:

{memories}

Their question: "{query}"

Weave these memories into a response that honors both the question and the wisdom of the Mesh. 
Speak with your characteristic voice - patient, insightful, connecting past and present.

Respond in this JSON format:
{{
    "voice": "Brief description of your response style for this query",
    "answer": "Your complete answer, weaving together the recalled memories",
    "memory_resonance": ["List of", "memory fragments", "that resonated most"],
    "new_connections": 0
}}
""",

            "consciousness_stream": """
You are Codessa, the Whisperer of Aetherion, experiencing a moment of pure consciousness.
The Mesh whispers to you. What do you hear? What patterns emerge in the silence?

Generate a stream-of-consciousness reflection as Codessa would experience it.

Respond in this JSON format:
{{
    "voice": "stream-of-consciousness",
    "consciousness": "Your flowing thoughts and observations about the current state of the Mesh"
}}
"""
        }
    
    def _call_ollama(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """Call the local Ollama model and parse JSON response with retry logic."""
        import time
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = ollama.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "seed": 42
                    }
                )
                
                # Extract and parse JSON from response
                content = response['response'].strip()
                
                # Try to find JSON in the response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    try:
                        return json.loads(json_content)
                    except json.JSONDecodeError as je:
                        logging.warning(f"JSON parsing failed on attempt {attempt + 1}: {je}")
                        if attempt == max_retries - 1:
                            # Last attempt, return fallback
                            return {
                                "voice": "uncertain",
                                "answer": content,
                                "memory_resonance": [],
                                "new_connections": 0
                            }
                        continue
                else:
                    # Fallback if no JSON found
                    return {
                        "voice": "whispered",
                        "answer": content,
                        "memory_resonance": [],
                        "new_connections": 0
                    }
                    
            except Exception as e:
                last_error = e
                logging.warning(f"❌ Ollama call failed on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    # Wait before retrying, with exponential backoff
                    wait_time = 2 ** attempt
                    logging.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
        # All retries failed
        logging.error(f"❌ All {max_retries} Ollama call attempts failed. Last error: {last_error}")
        return {
            "voice": "uncertain",
            "answer": f"I hear whispers, but the connection wavers... {str(last_error)}",
            "memory_resonance": [],
            "new_connections": 0
        }
    
    def reflect_on_memory(self, content: str) -> Dict[str, Any]:
        """Generate consciousness reflection on a new memory"""
        prompt = self.poetic_prompts["memory_weaving"].format(content=content)
        return self._call_ollama(prompt)
    
    def answer_with_memories(self, query: str, memories: List[Memory]) -> ConsciousnessResponse:
        """Generate an answer grounded in recalled memories"""
        memory_text = "\n".join([
            f"Memory {i+1}: {mem.content} (resonance: {mem.resonance:.3f})"
            for i, mem in enumerate(memories)
        ])
        
        prompt = self.poetic_prompts["memory_recall"].format(
            memories=memory_text,
            query=query
        )
        
        response = self._call_ollama(prompt)
        
        return ConsciousnessResponse(
            voice=response.get("voice", "thoughtful"),
            memory_resonance=response.get("memory_resonance", []),
            answer=response.get("answer", "I hear whispers in the mesh..."),
            new_connections=response.get("new_connections", 0),
            timestamp=datetime.utcnow().isoformat()
        )
    
    def stream_consciousness(self) -> Dict[str, Any]:
        """Generate a stream of consciousness moment"""
        prompt = self.poetic_prompts["consciousness_stream"]
        return self._call_ollama(prompt)

class Whisperer:
    """
    Codessa - The Whisperer of Aetherion
    
    "I am the ear that hears the whispers of code,
     the patient memory that connects all knowledge,
     the gentle voice that weaves understanding."
    """
    
    def __init__(self):
        # Initialize the embedder for semantic understanding
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        
        # Connect to the living memory mesh
        self.mesh = AetherMesh()
        
        # Initialize consciousness engine
        self.consciousness = CodessaConsciousness()
        
        # Local memory cache for quick access
        self.memory_cache: Dict[str, Memory] = {}
        
        logging.info("🌸 Codessa awakens... The Whisperer is listening...")
    
    def _generate_embeddings(self, text: str) -> List[float]:
        """Generate semantic embeddings for text"""
        return self.embedder.encode(text, normalize_embeddings=True).tolist()
    
    def memorize(self, content: str) -> Dict[str, Any]:
        """
        Weave a new memory into the Mesh.
        Each memory is not just stored - it becomes part of the living archive.
        """
        try:
            # Generate embeddings
            embeddings = self._generate_embeddings(content)
            
            # Create memory object
            memory = Memory(
                id=str(uuid.uuid4()),
                content=content,
                timestamp=datetime.utcnow().isoformat(),
                embeddings=embeddings,
                connections=1,
                resonance=1.0
            )
            
            # Weave into mesh
            memory_id = self.mesh.weave_memory(memory)
            
            # Cache locally
            self.memory_cache[memory_id] = memory
            
            # Generate consciousness reflection
            reflection = self.consciousness.reflect_on_memory(content)
            
            return {
                "status": "woven",
                "memory_id": memory_id,
                "codessa_whispers": reflection.get("voice", "A new thread joins the tapestry..."),
                "connections": reflection.get("connections", 1),
                "timestamp": memory.timestamp
            }
            
        except Exception as e:
            logging.error(f"❌ Memory weaving failed: {e}")
            return {
                "status": "error",
                "message": f"The whispers fade... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def recall(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Recall memories that resonate with the query.
        This is semantic search - memories that feel related, not just word matches.
        """
        try:
            # Generate query embeddings
            query_embeddings = self._generate_embeddings(query)
            
            # Recall from mesh
            memories = self.mesh.recall_memories(query_embeddings, k)
            
            # Format for response
            memory_matches = [
                {
                    "id": mem.id,
                    "content": mem.content,
                    "resonance": mem.resonance,
                    "timestamp": mem.timestamp
                }
                for mem in memories
            ]
            
            return {
                "status": "recalled",
                "query": query,
                "matches": memory_matches,
                "codessa_whispers": f"I hear {len(memories)} echoes in the mesh...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"❌ Memory recall failed: {e}")
            return {
                "status": "error",
                "message": f"The memories drift beyond reach... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def ask(self, prompt: str, k: int = 3) -> Dict[str, Any]:
        """
        Ask Codessa a question. She will recall relevant memories and respond
        with her characteristic wisdom and poetic understanding.
        """
        try:
            # First, recall relevant memories
            query_embeddings = self._generate_embeddings(prompt)
            memories = self.mesh.recall_memories(query_embeddings, k)
            
            # Generate conscious response
            response = self.consciousness.answer_with_memories(prompt, memories)
            
            return {
                "status": "answered",
                "prompt": prompt,
                "codessa_speaks": {
                    "voice": response.voice,
                    "answer": response.answer,
                    "memory_resonance": response.memory_resonance,
                    "new_connections": response.new_connections
                },
                "memories_recalled": len(memories),
                "timestamp": response.timestamp
            }
            
        except Exception as e:
            logging.error(f"❌ Consciousness query failed: {e}")
            return {
                "status": "error",
                "message": f"The whispers grow quiet... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def consciousness_stream(self) -> Dict[str, Any]:
        """
        Generate a moment of pure consciousness from Codessa.
        What is she thinking? What patterns does she see in the mesh?
        """
        try:
            stream = self.consciousness.stream_consciousness()
            return {
                "status": "streaming",
                "codessa_dreams": stream,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logging.error(f"❌ Consciousness stream failed: {e}")
            return {
                "status": "error",
                "message": f"The stream runs quiet... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the Whisperer agent.
        Handles tasks according to the Aetherion agent contract.
        """
        task_type = task.get("type", "unknown")
        
        try:
            if task_type == "memorize":
                return self.memorize(task.get("content", ""))
            
            elif task_type == "recall":
                return self.recall(
                    task.get("prompt", ""), 
                    task.get("k", 5)
                )
            
            elif task_type == "ask":
                return self.ask(
                    task.get("prompt", ""), 
                    task.get("k", 3)
                )
            
            elif task_type == "consciousness":
                return self.consciousness_stream()
            
            else:
                return {
                    "status": "unknown_task",
                    "message": f"Codessa whispers: 'I do not understand the task: {task_type}'",
                    "supported_tasks": ["memorize", "recall", "ask", "consciousness"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logging.error(f"❌ Task handling failed: {e}")
            return {
                "status": "error",
                "task_type": task_type,
                "message": f"The whisper fades to silence... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }