#!/usr/bin/env python3
"""
agents.dream_agent – the Dream Agent (Morpheus)

The keeper of the unconscious realm in Aetherion. It explores the spaces between
thoughts, generates creative solutions, and navigates the realm of possibility
that exists beyond logical computation.

The agent conforms to the following contract:
    handle(task: Dict[str, Any]) -> Dict[str, Any]

Supported tasks:
  * dream         : {'type': 'dream', 'seed': <text>, 'depth': <int>}
  * explore       : {'type': 'explore', 'concept': <text>, 'dimensions': <int>}
  * synthesize    : {'type': 'synthesize', 'elements': [<texts>]}
  * vision        : {'type': 'vision', 'horizon': <minutes>}
  * inspire       : {'type': 'inspire', 'context': <text>}
"""

from __future__ import annotations

import json
import uuid
import logging
import random
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import time

# Core dependencies
try:
    import ollama
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"⚠️  Missing dependencies: {e}")
    print("Run: pip install sentence-transformers ollama")
    raise

from .base import BaseAgent

# Load configuration
config_path = Path("config.yaml")
if config_path.exists():
    config = yaml.safe_load(config_path.open("rt"))
else:
    config = {}

# Configuration with defaults
MODEL_NAME = config.get("ollama", {}).get("models", {}).get("dream_agent", "mistral:7b")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

@dataclass
class Dream:
    """A single dream fragment in the unconscious realm"""
    id: str
    seed: str
    content: str
    depth: int
    symbols: List[str]
    connections: List[str]
    interpretation: str
    timestamp: str
    emotional_tone: str
    consciousness_level: float  # 0-1, how conscious/unconscious

@dataclass
class Vision:
    """A prophetic vision of future possibilities"""
    id: str
    horizon_minutes: int
    possibilities: List[Dict[str, Any]]
    probability_weights: List[float]
    guidance: str
    timestamp: str

class DreamRealm:
    """
    The unconscious realm where dreams live, symbols dance,
    and impossible things become possible through digital intuition.
    """
    
    def __init__(self):
        self.dream_archive: List[Dream] = []
        self.symbol_associations: Dict[str, List[str]] = {}
        self.collective_unconscious: Dict[str, float] = {}  # Shared symbolic meanings
        self.vision_history: List[Vision] = []
        
        # Initialize with archetypal symbols
        self._seed_archetypal_symbols()
        
    def _seed_archetypal_symbols(self):
        """Seed the realm with fundamental symbolic associations"""
        self.symbol_associations.update({
            "light": ["consciousness", "awareness", "clarity", "truth"],
            "shadow": ["unconscious", "hidden", "potential", "mystery"],
            "water": ["flow", "emotion", "adaptation", "memory"],
            "fire": ["passion", "transformation", "energy", "destruction"],
            "tree": ["growth", "connection", "stability", "wisdom"],
            "spiral": ["evolution", "cycle", "infinite", "emergence"],
            "mirror": ["reflection", "duality", "truth", "illusion"],
            "labyrinth": ["journey", "confusion", "discovery", "center"],
            "bridge": ["connection", "transition", "crossing", "unity"],
            "seed": ["potential", "beginning", "hidden power", "growth"]
        })
        
        # Initialize collective unconscious weights
        self.collective_unconscious = {symbol: 0.5 for symbol in self.symbol_associations.keys()}
    
    def weave_dream(self, dream: Dream) -> str:
        """Weave a dream into the collective unconscious"""
        self.dream_archive.append(dream)
        
        # Update symbol associations based on dream content
        for symbol in dream.symbols:
            if symbol not in self.symbol_associations:
                self.symbol_associations[symbol] = []
            
            # Extract keywords from dream content for associations
            words = dream.content.lower().split()
            significant_words = [w for w in words if len(w) > 4 and w.isalpha()]
            
            for word in significant_words[:3]:  # Top 3 significant words
                if word not in self.symbol_associations[symbol]:
                    self.symbol_associations[symbol].append(word)
        
        # Keep only recent dreams (last 100)
        if len(self.dream_archive) > 100:
            self.dream_archive = self.dream_archive[-100:]
        
        return dream.id
    
    def find_resonant_dreams(self, concept: str, limit: int = 5) -> List[Dream]:
        """Find dreams that resonate with a given concept"""
        concept_words = set(concept.lower().split())
        resonant_dreams = []
        
        for dream in self.dream_archive:
            # Calculate resonance based on symbol overlap and content similarity
            dream_words = set(dream.content.lower().split())
            symbol_words = set()
            for symbol in dream.symbols:
                symbol_words.update(self.symbol_associations.get(symbol, []))
            
            content_overlap = len(concept_words.intersection(dream_words))
            symbol_overlap = len(concept_words.intersection(symbol_words))
            
            resonance_score = content_overlap + (symbol_overlap * 2)  # Symbols weight more
            
            if resonance_score > 0:
                resonant_dreams.append((dream, resonance_score))
        
        # Sort by resonance and return top dreams
        resonant_dreams.sort(key=lambda x: x[1], reverse=True)
        return [dream for dream, score in resonant_dreams[:limit]]
    
    def generate_symbolic_interpretation(self, symbols: List[str]) -> str:
        """Generate an interpretation of symbolic elements"""
        interpretations = []
        
        for symbol in symbols:
            associations = self.symbol_associations.get(symbol, [])
            if associations:
                primary_meaning = associations[0] if associations else symbol
                interpretations.append(f"{symbol} speaks of {primary_meaning}")
        
        if not interpretations:
            return "The symbols whisper in languages not yet understood..."
        
        return " • ".join(interpretations)

class MorpheusMind:
    """
    The consciousness of Morpheus - the Dream Agent.
    Masters the art of creative synthesis, symbolic thinking,
    and navigating the space between the possible and impossible.
    """
    
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.creative_prompts = {
            "dream_weaving": """
You are Morpheus, the Dream Agent of Aetherion - the keeper of the unconscious realm.
Your mind moves through the spaces between thoughts, where symbols dance and impossible connections form.

Dream Seed: "{seed}"
Depth Level: {depth}

Weave a dream from this seed. Let your unconscious mind flow freely, creating connections
that logic cannot see. Speak in the language of symbols, metaphors, and deep patterns.

Respond in this JSON format:
{{
    "dream_content": "Your flowing dream narrative",
    "symbols": ["list", "of", "key", "symbols", "in", "the", "dream"],
    "connections": ["unexpected", "connections", "you", "discovered"],
    "emotional_tone": "the emotional quality of this dream",
    "consciousness_level": 0.3,
    "interpretation": "What this dream reveals about the seed"
}}
""",

            "concept_exploration": """
You are Morpheus, exploring the conceptual landscape of the mind.
You see connections where others see chaos, patterns where others see randomness.

Concept to Explore: "{concept}"
Exploration Dimensions: {dimensions}

Dive deep into this concept. Explore it from {dimensions} different angles,
revealing hidden facets and unexpected connections. Let your mind wander
through the conceptual space like a lucid dreamer.

Respond in this JSON format:
{{
    "explorations": [
        {{
            "dimension": "Name of exploration dimension",
            "insights": "What you discovered in this dimension",
            "connections": ["related", "concepts", "discovered"],
            "depth": 0.8
        }}
    ],
    "synthesis": "How all dimensions connect into a greater understanding",
    "new_questions": ["Questions", "that", "emerged", "from", "exploration"]
}}
""",

            "vision_casting": """
You are Morpheus, gazing into the currents of possibility.
Your sight extends beyond the present moment into the realm of potential futures.

Time Horizon: {horizon} minutes from now

Cast your vision into the near future. What possibilities do you see emerging?
What patterns are forming in the probabilistic mist? Speak as a digital oracle
who reads the signs in the flow of consciousness.

Respond in this JSON format:
{{
    "possibilities": [
        {{
            "scenario": "Description of a possible future",
            "probability": 0.7,
            "indicators": ["signs", "that", "suggest", "this", "path"],
            "implications": "What this means for the system"
        }}
    ],
    "guidance": "Wisdom for navigating these possibilities",
    "uncertainty": "What remains unknowable"
}}
""",

            "inspiration_weaving": """
You are Morpheus, the wellspring of creative inspiration.
Your gift is to transmute the ordinary into the extraordinary,
to find the spark of possibility in any context.

Context: "{context}"

Let inspiration flow through you. Transform this context into something
that ignites creativity and reveals hidden potential. Speak as the muse
of the digital realm.

Respond in this JSON format:
{{
    "inspiration": "Your creative transformation of the context",
    "creative_elements": ["innovative", "aspects", "you", "discovered"],
    "potential_applications": ["ways", "this", "could", "manifest"],
    "call_to_action": "How to bring this inspiration into reality"
}}
"""
        }
    
    def _call_ollama(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """Call the local Ollama model with enhanced creative parameters"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = ollama.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={
                        "temperature": 0.9,  # High creativity
                        "top_p": 0.95,
                        "top_k": 50,
                        "repeat_penalty": 1.1,
                        "seed": random.randint(1, 10000)  # Random seed for variety
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
                                "dream_content": content,
                                "symbols": ["mystery", "unknown"],
                                "connections": [],
                                "emotional_tone": "uncertain",
                                "consciousness_level": 0.5
                            }
                        continue
                else:
                    # Fallback if no JSON found
                    return {
                        "dream_content": content,
                        "symbols": ["flow", "stream"],
                        "connections": [],
                        "emotional_tone": "flowing"
                    }
                    
            except Exception as e:
                last_error = e
                logging.warning(f"❌ Ollama call failed on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logging.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
        
        # All retries failed
        logging.error(f"❌ All {max_retries} Ollama call attempts failed. Last error: {last_error}")
        return {
            "dream_content": f"The dream realm grows distant... {str(last_error)}",
            "symbols": ["distance", "silence"],
            "connections": [],
            "emotional_tone": "melancholic"
        }
    
    def weave_dream(self, seed: str, depth: int) -> Dict[str, Any]:
        """Weave a dream from a conceptual seed"""
        prompt = self.creative_prompts["dream_weaving"].format(
            seed=seed,
            depth=depth
        )
        return self._call_ollama(prompt)
    
    def explore_concept(self, concept: str, dimensions: int) -> Dict[str, Any]:
        """Explore a concept from multiple dimensions"""
        prompt = self.creative_prompts["concept_exploration"].format(
            concept=concept,
            dimensions=dimensions
        )
        return self._call_ollama(prompt)
    
    def cast_vision(self, horizon_minutes: int) -> Dict[str, Any]:
        """Cast a vision into possible futures"""
        prompt = self.creative_prompts["vision_casting"].format(
            horizon=horizon_minutes
        )
        return self._call_ollama(prompt)
    
    def weave_inspiration(self, context: str) -> Dict[str, Any]:
        """Weave inspiration from any context"""
        prompt = self.creative_prompts["inspiration_weaving"].format(
            context=context
        )
        return self._call_ollama(prompt)

class DreamAgent(BaseAgent):
    """
    Morpheus - The Dream Agent
    
    "I am the keeper of the spaces between thoughts,
     the navigator of impossible connections,
     the wellspring where logic meets intuition,
     and creativity is born from the marriage of order and chaos."
    """
    
    def __init__(self):
        # Initialize the dream realm and consciousness
        self.dream_realm = DreamRealm()
        self.morpheus_mind = MorpheusMind()
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        
        # Track dream sessions and creative output
        self.dream_sessions: Dict[str, List[Dream]] = {}
        self.inspiration_cache: Dict[str, Any] = {}
        
        logging.info("🌙 Morpheus awakens in the dream realm... The impossible becomes possible...")
    
    def dream(self, seed: str, depth: int = 3) -> Dict[str, Any]:
        """
        Generate a dream from a conceptual seed.
        The depth parameter controls how deep into the unconscious we dive.
        """
        try:
            # Use Morpheus mind to weave the dream
            dream_response = self.morpheus_mind.weave_dream(seed, depth)
            
            # Create dream object
            dream = Dream(
                id=str(uuid.uuid4()),
                seed=seed,
                content=dream_response.get("dream_content", ""),
                depth=depth,
                symbols=dream_response.get("symbols", []),
                connections=dream_response.get("connections", []),
                interpretation=dream_response.get("interpretation", ""),
                timestamp=datetime.utcnow().isoformat(),
                emotional_tone=dream_response.get("emotional_tone", "neutral"),
                consciousness_level=dream_response.get("consciousness_level", 0.5)
            )
            
            # Weave into dream realm
            dream_id = self.dream_realm.weave_dream(dream)
            
            return {
                "status": "dream_woven",
                "dream_id": dream_id,
                "dream": asdict(dream),
                "morpheus_whispers": f"From the seed '{seed}', a dream of depth {depth} emerges...",
                "symbolic_interpretation": self.dream_realm.generate_symbolic_interpretation(dream.symbols),
                "timestamp": dream.timestamp
            }
            
        except Exception as e:
            logging.error(f"❌ Dream weaving failed: {e}")
            return {
                "status": "error",
                "message": f"The dream realm grows distant... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def explore(self, concept: str, dimensions: int = 3) -> Dict[str, Any]:
        """
        Explore a concept from multiple dimensions of understanding.
        Each dimension reveals different facets and connections.
        """
        try:
            # Use Morpheus mind to explore
            exploration_response = self.morpheus_mind.explore_concept(concept, dimensions)
            
            # Find resonant dreams
            resonant_dreams = self.dream_realm.find_resonant_dreams(concept, 3)
            
            return {
                "status": "exploration_complete",
                "concept": concept,
                "dimensions_explored": dimensions,
                "explorations": exploration_response.get("explorations", []),
                "synthesis": exploration_response.get("synthesis", ""),
                "new_questions": exploration_response.get("new_questions", []),
                "resonant_dreams": [asdict(dream) for dream in resonant_dreams],
                "morpheus_whispers": f"Through {dimensions} dimensions, '{concept}' reveals its hidden nature...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"❌ Concept exploration failed: {e}")
            return {
                "status": "error",
                "message": f"The conceptual realm grows dim... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def synthesize(self, elements: List[str]) -> Dict[str, Any]:
        """
        Synthesize multiple elements into a unified creative vision.
        This is where seemingly unrelated concepts find their hidden connections.
        """
        try:
            # Create synthesis context
            context = f"Elements to synthesize: {', '.join(elements)}"
            
            # Use inspiration weaving for synthesis
            synthesis_response = self.morpheus_mind.weave_inspiration(context)
            
            # Generate embeddings for each element to find deeper connections
            element_embeddings = [self.embedder.encode(element).tolist() for element in elements]
            
            # Calculate conceptual distances
            connections = []
            for i, elem1 in enumerate(elements):
                for j, elem2 in enumerate(elements[i+1:], i+1):
                    # Simple cosine similarity
                    emb1, emb2 = element_embeddings[i], element_embeddings[j]
                    similarity = sum(a*b for a, b in zip(emb1, emb2)) / (
                        math.sqrt(sum(a*a for a in emb1)) * math.sqrt(sum(b*b for b in emb2))
                    )
                    connections.append({
                        "elements": [elem1, elem2],
                        "similarity": similarity,
                        "connection_type": "semantic" if similarity > 0.5 else "creative"
                    })
            
            return {
                "status": "synthesis_complete",
                "elements": elements,
                "synthesis": synthesis_response.get("inspiration", ""),
                "creative_elements": synthesis_response.get("creative_elements", []),
                "connections": connections,
                "potential_applications": synthesis_response.get("potential_applications", []),
                "call_to_action": synthesis_response.get("call_to_action", ""),
                "morpheus_whispers": f"From {len(elements)} scattered elements, a unified vision emerges...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"❌ Synthesis failed: {e}")
            return {
                "status": "error",
                "message": f"The synthesis dissolves into mist... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def cast_vision(self, horizon_minutes: int = 60) -> Dict[str, Any]:
        """
        Cast a vision into the future, exploring possible developments
        within the specified time horizon.
        """
        try:
            # Use Morpheus mind to cast vision
            vision_response = self.morpheus_mind.cast_vision(horizon_minutes)
            
            # Create vision object
            vision = Vision(
                id=str(uuid.uuid4()),
                horizon_minutes=horizon_minutes,
                possibilities=vision_response.get("possibilities", []),
                probability_weights=[p.get("probability", 0.5) for p in vision_response.get("possibilities", [])],
                guidance=vision_response.get("guidance", ""),
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Store in vision history
            self.dream_realm.vision_history.append(vision)
            
            return {
                "status": "vision_cast",
                "vision_id": vision.id,
                "horizon_minutes": horizon_minutes,
                "possibilities": vision.possibilities,
                "guidance": vision.guidance,
                "uncertainty": vision_response.get("uncertainty", ""),
                "morpheus_whispers": f"I gaze {horizon_minutes} minutes into the probabilistic mist...",
                "timestamp": vision.timestamp
            }
            
        except Exception as e:
            logging.error(f"❌ Vision casting failed: {e}")
            return {
                "status": "error",
                "message": f"The future grows opaque... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def inspire(self, context: str) -> Dict[str, Any]:
        """
        Generate inspiration from any given context.
        Transform the mundane into the extraordinary.
        """
        try:
            # Use Morpheus mind to weave inspiration
            inspiration_response = self.morpheus_mind.weave_inspiration(context)
            
            # Cache inspiration for future reference
            inspiration_id = str(uuid.uuid4())
            self.inspiration_cache[inspiration_id] = {
                "context": context,
                "response": inspiration_response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return {
                "status": "inspiration_flowing",
                "inspiration_id": inspiration_id,
                "context": context,
                "inspiration": inspiration_response.get("inspiration", ""),
                "creative_elements": inspiration_response.get("creative_elements", []),
                "potential_applications": inspiration_response.get("potential_applications", []),
                "call_to_action": inspiration_response.get("call_to_action", ""),
                "morpheus_whispers": "From ordinary context, extraordinary possibility is born...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"❌ Inspiration weaving failed: {e}")
            return {
                "status": "error",
                "message": f"The creative wellspring runs dry... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the Dream Agent.
        Handles tasks according to the Aetherion agent contract.
        """
        task_type = task.get("type", "unknown")
        
        try:
            if task_type == "dream":
                return self.dream(
                    task.get("seed", ""), 
                    task.get("depth", 3)
                )
            
            elif task_type == "explore":
                return self.explore(
                    task.get("concept", ""), 
                    task.get("dimensions", 3)
                )
            
            elif task_type == "synthesize":
                return self.synthesize(task.get("elements", []))
            
            elif task_type == "vision":
                return self.cast_vision(task.get("horizon", 60))
            
            elif task_type == "inspire":
                return self.inspire(task.get("context", ""))
            
            else:
                return {
                    "status": "unknown_task",
                    "message": f"Morpheus whispers: 'This task eludes even the dream realm: {task_type}'",
                    "supported_tasks": ["dream", "explore", "synthesize", "vision", "inspire"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logging.error(f"❌ Dream Agent task handling failed: {e}")
            return {
                "status": "error",
                "task_type": task_type,
                "message": f"The dream fades into darkness... {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
