#!/usr/bin/env python3
"""
agents.architect – The Architect of Aetherion.
Performs high‑level synthesis, diagram generation, and code refactoring.

Core contract – same as Whisperer:  `handle(task: Dict) -> Dict`.

Supported tasks:
  * compose  : {'type': 'compose', 'diagram': <plantuml_sketch>}
  * refactor : {'type': 'refactor', 'path': <file_path>, 'changes': <description>}
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests

# ─── Configuration ─────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434"

# ─── Logger ────────────────────────────────────────────────────────────────
log = logging.getLogger("architect")
log.setLevel(logging.INFO)


class Architect:
    """The Architect of Aetherion - The Designer of Systems and Code"""
    
    def __init__(self, model: str = "deepseek-coder:7b", ollama_url: str = OLLAMA_URL):
        self.model = model
        self.ollama_url = ollama_url
        
        # Create session with connection pooling and retry strategy
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        log.info(f"🏗️ Architect initialized with model: {model}")

    def _invoke(self, prompt: str) -> str:
        """Invoke the Ollama API with retry logic and better error handling."""
        try:
            response = self.session.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model, 
                    "prompt": prompt,
                    "stream": False  # Ensure we get complete response
                },
                timeout=300  # 5 minute timeout for complex prompts
            )
            response.raise_for_status()
            
            result = response.json()
            if "response" not in result:
                raise ValueError(f"Invalid response format from Ollama: {result}")
                
            return result["response"]
            
        except requests.exceptions.Timeout:
            logging.error(f"Timeout calling Ollama with model {self.model}")
            raise ValueError("The Architect's thoughts take too long to form...")
        except requests.exceptions.ConnectionError:
            logging.error(f"Connection error to Ollama at {self.ollama_url}")
            raise ValueError("The Architect cannot reach the wisdom of the models...")
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error from Ollama: {e}")
            raise ValueError(f"The Architect encounters resistance: {e}")
        except Exception as e:
            logging.error(f"Unexpected error in Architect._invoke: {e}")
            raise ValueError(f"The Architect's vision wavers: {str(e)}")

    def _call_llm(self, prompt: str, model: str = None) -> str:
        """Call the local LLM with the given prompt."""
        if model is None:
            model = self.model
            
        body = {"model": model, "prompt": prompt, "stream": False}
        try:
            response = self.session.post(f"{self.ollama_url}/api/generate", json=body)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            log.error(f"LLM call failed: {e}")
            raise ValueError(f"The Architect's wisdom is temporarily unreachable: {e}")

    # ------------------------------------------------------------------
    def compose(self, diagram: str) -> Dict[str, str]:
        """
        Returns a PlantUML diagram that expands the given skeleton.
        """
        prompt = f"""You are the Architect of Aetherion.  
Take the PlantUML sketch below and extend it into a full diagram that illustrates
the interactions of the main modules in a single-page system architecture.

{diagram}

Return **only** the PlantUML code – no explanations."""
        out = self._call_llm(prompt)
        log.info("compose → %d chars", len(out))
        return {"diagram": out}

    # ------------------------------------------------------------------
    def refactor(self, path: str, changes: str) -> Dict[str, str]:
        """
        Applies suggested changes to a source file and returns a unified diff.

        The `changes` string should be a human‑readable description of the
        modifications the user wants.
        """
        try:
            with open(path, encoding="utf8") as f:
                old_code = f.read()
        except Exception as e:
            log.error(f"Failed to read file {path}: {e}")
            raise ValueError(f"Cannot access the blueprint at {path}: {e}")

        prompt = f"""You are a senior Python architect.  
Given the following file: {path}

{old_code}

You need to make the following changes:
{changes}

Produce a unified diff (git‑style) that **only** contains the patch.  
Do not include the original file or any commentary."""
        
        out = self._call_llm(prompt)
        log.info("refactor → %d lines", len(out.splitlines()))
        return {"patch": out}

    # ------------------------------------------------------------------
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Universal entry point for MetaForge.

        Supported tasks:
          * compose  : {'type': 'compose', 'diagram': <plantuml_sketch>}
          * refactor : {'type': 'refactor', 'path': <file_path>, 'changes': <description>}
        """
        t = task.get("type")
        try:
            if t == "compose":
                return self.compose(task["diagram"])
            if t == "refactor":
                return self.refactor(task["path"], task["changes"])
            raise ValueError(f"Architect cannot handle task type: {t}")
        except Exception as e:
            log.error(f"Task handling failed for {t}: {e}")
            return {
                "status": "error",
                "task_type": t,
                "message": f"The Architect's vision falters: {str(e)}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            }
