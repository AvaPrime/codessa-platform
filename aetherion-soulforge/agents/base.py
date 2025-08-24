#!/usr/bin/env python3
"""
Base Agent class for Aetherion

Provides a common interface for all agents in the Aetherion ecosystem.
Each agent should inherit from this base class and implement the handle method.
"""

from typing import Dict, Any
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    Abstract base class for all Aetherion agents.
    
    All agents in the Aetherion ecosystem should inherit from this class
    and implement the handle method to process tasks according to their
    specific capabilities.
    """
    
    @abstractmethod
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task and return a response.
        
        Args:
            task: A dictionary containing task information including:
                - type: The type of task to perform
                - Additional task-specific parameters
                
        Returns:
            A dictionary containing the response with at least:
                - status: The status of the task processing
                - Additional response data
        """
        pass