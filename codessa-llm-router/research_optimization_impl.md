# Path C: Research & Optimization Implementation

This document outlines the implementation of advanced research and optimization capabilities for the Codessa Dynamic LLM Router, focusing on reinforcement learning, predictive analytics, automated optimization, and cutting-edge routing techniques.

---

## 0) Research Platform Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Research & Optimization Layer             │
├─────────────────┬─────────────────┬─────────────────────────┤
│ RL Agent        │ Predictive      │ Auto-Optimization       │
│ - Q-Learning    │ Analytics       │ - Pareto Frontier       │
│ - Policy Grad   │ - Load Predict  │ - Prompt Engineering    │
│ - Multi-Armed   │ - Quality Pred  │ - Rule Discovery        │
│ Bandit          │ - Cost Forecast │ - A/B Testing           │
├─────────────────┼─────────────────┼─────────────────────────┤
│           Enhanced Router Core with ML Pipeline             │
│ - Feature Eng   │ - Experiment    │ - Model Perf Tracking   │
│ - Real-time     │ - Multi-armed   │ - Continuous Learning   │
│   Learning      │   Bandits       │ - Adaptive Thresholds   │
└─────────────────────────────────────────────────────────────┘
```

**Core Research Areas:**
- **Reinforcement Learning for Dynamic Routing**: Learn optimal routing policies through interaction
- **Predictive Performance Modeling**: Forecast model performance, latency, and costs
- **Automated Prompt Engineering**: Discover optimal prompts and routing rules
- **Multi-Objective Optimization**: Balance cost, quality, latency, and user satisfaction
- **Advanced Experimentation**: Sophisticated A/B testing with statistical rigor

---

## 1) Reinforcement Learning Framework

### RL Environment for Router Optimization

**`/research/rl/environment.py`**
```python
import gym
from gym import spaces
import numpy as np
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime, timedelta

class ActionSpace(Enum):
    """Available routing actions"""
    ROUTE_TO_CHEAP = 0
    ROUTE_TO_BALANCED = 1  
    ROUTE_TO_STRONG = 2
    ROUTE_TO_SPECIALIST = 3
    CASCADE_ENABLED = 4
    CASCADE_DISABLED = 5

@dataclass
class RouterState:
    """State representation for RL agent"""
    # Request features
    query_complexity: float  # 0-1 normalized
    query_length: int
    domain: str  # encoded as categorical
    user_tier: int  # 0=free, 1=pro, 2=enterprise
    
    # Context features  
    recent_success_rate: float
    current_load: float  # normalized system load
    cost_budget_remaining: float  # 0-1
    time_of_day: float  # 0-1 normalized
    
    # Historical features
    user_satisfaction_history: float  # rolling average
    cascade_rate: float
    cache_hit_rate: float
    
@dataclass 
class RouterReward:
    """Multi-objective reward signal"""
    quality_score: float  # -1 to 1
    cost_efficiency: float  # -1 to 1 
    latency_score: float  # -1 to 1
    user_satisfaction: float  # -1 to 1
    
    def composite_reward(self, weights: Dict[str, float] = None) -> float:
        """Compute weighted composite reward"""
        if weights is None:
            weights = {"quality": 0.4, "cost": 0.2, "latency": 0.2, "satisfaction": 0.2}
            
        return (
            self.quality_score * weights["quality"] +
            self.cost_efficiency * weights["cost"] + 
            self.latency_score * weights["latency"] +
            self.user_satisfaction * weights["satisfaction"]
        )

class RouterEnvironment(gym.Env):
    """Gym environment for training routing policies"""
    
    def __init__(self, router_client, evaluation_client, config: Dict):
        super().__init__()
        
        self.router = router_client
        self.evaluator = evaluation_client
        self.config = config
        
        # Define action and observation spaces
        self.action_space = spaces.Discrete(len(ActionSpace))
        
        # State space: normalized features
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, 
            shape=(12,),  # Number of state features
            dtype=np.float32
        )
        
        # Episode tracking
        self.episode_length = config.get("episode_length", 100)
        self.current_step = 0
        self.episode_rewards = []
        self.state_history = []
        
    def reset(self) -> np.ndarray:
        """Reset environment for new episode"""
        self.current_step = 0
        self.episode_rewards = []
        self.state_history = []
        
        # Get initial state from real system
        state = self._get_current_state()
        return self._state_to_observation(state)
        
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute action and return next state, reward, done, info"""
        # Convert action to routing decision
        routing_action = ActionSpace(action)
        
        # Get current state
        current_state = self._get_current_state()
        
        # Execute routing decision on real system
        request = self._generate_test_request(current_state)
        routing_result = self._execute_routing_action(request, routing_action)
        
        # Calculate reward based on actual outcome
        reward_components = self._calculate_reward(routing_result, current_state)
        reward = reward_components.composite_reward(self.config.get("reward_weights"))
        
        # Get next state
        next_state = self._get_current_state()
        
        # Episode management
        self.current_step += 1
        self.episode_rewards.append(reward)
        self.state_history.append(current_state)
        
        done = self.current_step >= self.episode_length
        
        info = {
            "routing_result": routing_result,
            "reward_components": reward_components,
            "episode_step": self.current_step,
            "cumulative_reward": sum(self.episode_rewards)
        }
        
        return self._state_to_observation(next_state), reward, done, info
        
    def _get_current_state(self) -> RouterState:
        """Get current system state for RL agent"""
        # This would integrate with your monitoring/metrics system
        metrics = asyncio.run(self.router.get_system_metrics())
        
        return RouterState(
            query_complexity=0.5,  # Would be computed from recent queries
            query_length=metrics.get("avg_query_length", 100),
            domain="general",  # Most common recent domain
            user_tier=1,  # Average user tier
            recent_success_rate=metrics.get("success_rate", 0.95),
            current_load=metrics.get("system_load", 0.3),
            cost_budget_remaining=metrics.get("budget_remaining", 0.8),
            time_of_day=datetime.now().hour / 24.0,
            user_satisfaction_history=metrics.get("satisfaction", 0.8),
            cascade_rate=metrics.get("cascade_rate", 0.1),
            cache_hit_rate=metrics.get("cache_hit_rate", 0.3)
        )
        
    def _state_to_observation(self, state: RouterState) -> np.ndarray:
        """Convert RouterState to numpy observation"""
        # Encode categorical domain
        domain_encoding = {"general": 0, "code": 1, "rag": 2, "qa": 3}.get(state.domain, 0)
        
        obs = np.array([
            state.query_complexity,
            min(state.query_length / 1000.0, 1.0),  # Normalize query length
            domain_encoding / 3.0,  # Normalize domain
            state.user_tier / 2.0,  # Normalize tier
            state.recent_success_rate,
            state.current_load,
            state.cost_budget_remaining,
            state.time_of_day,
            state.user_satisfaction_history,
            state.cascade_rate,
            state.cache_hit_rate,
            np.random.random()  # Add some noise for exploration
        ], dtype=np.float32)
        
        return obs
        
    def _execute_routing_action(self, request: Dict, action: ActionSpace) -> Dict:
        """Execute routing action on real system"""
        # Modify request based on action
        if action == ActionSpace.ROUTE_TO_CHEAP:
            request["model"] = "mistral-small"
        elif action == ActionSpace.ROUTE_TO_BALANCED:
            request["model"] = "claude-3-7"
        elif action == ActionSpace.ROUTE_TO_STRONG:
            request["model"] = "gpt-5"
        elif action == ActionSpace.ROUTE_TO_SPECIALIST:
            # Choose specialist model based on domain
            domain = request.get("metadata", {}).get("domain", "general")
            specialist_models = {
                "code": "claude-3-7",
                "rag": "gpt-5", 
                "qa": "claude-3-7"
            }
            request["model"] = specialist_models.get(domain, "claude-3-7")
        elif action == ActionSpace.CASCADE_ENABLED:
            request["metadata"]["enable_cascade"] = True
        elif action == ActionSpace.CASCADE_DISABLED:
            request["metadata"]["enable_cascade"] = False
            
        # Execute request
        result = asyncio.run(self.router.chat_completions(request))
        return result
        
    def _calculate_reward(self, routing_result: Dict, state: RouterState) -> RouterReward:
        """Calculate multi-objective reward based on routing outcome"""
        # Quality score based on success and potential cascade
        quality_score = 1.0 if routing_result.get("ok", True) else -1.0
        if routing_result.get("cascade_from"):
            quality_score *= 0.8  # Slight penalty for cascade
            
        # Cost efficiency: reward lower costs, penalize budget overrun
        cost = routing_result.get("cost", {}).get("estimated_usd", 0.001)
        target_cost = 0.002  # Target cost per request
        cost_efficiency = max(-1.0, min(1.0, (target_cost - cost) / target_cost))
        