# Codessa AI-Native Development Platform Implementation

This implementation transforms the existing Codessa Dynamic LLM Router into a comprehensive AI-native development platform with agent orchestration, workflow automation, and extensive integrations.

---

## 0) Platform Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   AI-Native Platform                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Agent Orchestra │ Workflow Engine │ Integration Hub         │
│ - Multi-agent   │ - Event-driven  │ - Slack, Discord        │
│ - Specialized   │ - Git triggers  │ - Notion, Confluence    │
│ - Collaborative │ - Schedules     │ - Jira, Linear         │
├─────────────────┼─────────────────┼─────────────────────────┤
│           Enhanced Router Core                              │
│ - Agent routing │ - Context mgmt  │ - Custom models         │
│ - Tool calling  │ - State persist │ - Fine-tuning           │
└─────────────────────────────────────────────────────────────┘
```

**Key Platform Components:**
- **Agent Orchestration**: Coordinate specialized AI agents for complex development tasks
- **Workflow Automation**: Event-driven workflows with Git, Slack, and other integrations
- **Integration Marketplace**: Pre-built connectors for developer tools and platforms
- **Custom Model Pipeline**: Automated fine-tuning for organization-specific needs

---

## 1) Agent Orchestration System

### Core Agent Framework

**`/platform/agents/orchestrator.py`**
```python
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import logging
from datetime import datetime, timedelta
import uuid

class AgentCapability(Enum):
    CODE_REVIEW = "code_review"
    CODE_GENERATION = "code_generation"
    DOCUMENTATION = "documentation"
    SECURITY_ANALYSIS = "security_analysis"
    TESTING = "testing"
    DEBUGGING = "debugging"
    INFRASTRUCTURE = "infrastructure"
    PROJECT_PLANNING = "project_planning"
    ARCHITECTURE_DESIGN = "architecture_design"
    API_DESIGN = "api_design"
    DATABASE_DESIGN = "database_design"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"

@dataclass
class AgentTask:
    """Represents a task to be executed by an AI agent"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requester_id: str = ""
    capability: AgentCapability = AgentCapability.CODE_GENERATION
    input_data: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 3  # 1=highest, 5=lowest
    parent_task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    timeout_minutes: int = 15
    retry_count: int = 0
    max_retries: int = 2
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class AgentResponse:
    """Response from an AI agent after task execution"""
    task_id: str
    agent_id: str
    success: bool
    output: Dict[str, Any]
    confidence: float = 0.0
    execution_time_ms: int = 0
    follow_up_tasks: List[AgentTask] = field(default_factory=list)
    context_updates: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    resources_used: Dict[str, Any] = field(default_factory=dict)

class AgentOrchestrator:
    """Central coordinator for all AI agents in the platform"""
    
    def __init__(self, router_client, context_store, integration_hub):
        self.router = router_client
        self.context = context_store
        self.integrations = integration_hub
        
        # Agent registry
        self.agents: Dict[str, Dict] = {}
        
        # Task management
        self.task_queue = asyncio.PriorityQueue()
        self.active_tasks: Dict[str, Dict] = {}
        self.completed_tasks: Dict[str, AgentResponse] = {}
        
        # Performance tracking
        self.agent_metrics: Dict[str, Dict] = {}
        
        # Multi-agent coordination
        self.coordinator = MultiAgentCoordinator(self)
        
    async def register_agent(self, agent_id: str, agent_instance, capabilities: List[AgentCapability]):
        """Register a specialized agent with the orchestrator"""
        self.agents[agent_id] = {
            "instance": agent_instance,
            "capabilities": capabilities,
            "active_tasks": 0,
            "max_concurrent": getattr(agent_instance, 'max_concurrent', 3),
            "success_rate": 1.0,
            "avg_execution_time": 5000,  # milliseconds
            "last_used": datetime.utcnow(),
            "total_tasks": 0
        }
        
        # Initialize metrics
        self.agent_metrics[agent_id] = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0,
            "avg_confidence": 0.8,
            "capability_performance": {}
        }
        
        logging.info(f"Registered agent {agent_id} with capabilities: {[c.value for c in capabilities]}")
        
    async def submit_task(self, task: AgentTask) -> str:
        """Submit a task for agent processing"""
        # Validate task
        if not task.task_id:
            task.task_id = str(uuid.uuid4())
            
        # Store context
        await self.context.store_task_context(task.task_id, task.context)
        
        # Check for multi-agent collaboration needs
        if await self._requires_collaboration(task):
            return await self.coordinator.handle_collaborative_task(task)
        
        # Add to priority queue (lower priority number = higher priority)
        await self.task_queue.put((task.priority, task.created_at.timestamp(), task))
        
        logging.info(f"Submitted task {task.task_id} with capability {task.capability.value}")
        return task.task_id
        
    async def get_task_result(self, task_id: str, timeout: int = 300) -> Optional[AgentResponse]:
        """Wait for task completion and return result"""
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
            await asyncio.sleep(0.5)
            
        return None  # Timeout
        
    async def _requires_collaboration(self, task: AgentTask) -> bool:
        """Determine if task requires multiple specialized agents"""
        collaboration_keywords = [
            "full stack", "end-to-end", "comprehensive review",
            "design and implement", "analyze and fix", "complete solution",
            "frontend and backend", "database and api", "deployment pipeline"
        ]
        
        task_description = json.dumps(task.input_data).lower()
        
        # Check for multiple capability requirements
        mentioned_capabilities = sum(1 for cap in AgentCapability if cap.value in task_description)
        if mentioned_capabilities >= 2:
            return True
            
        # Check for collaboration keywords
        return any(keyword in task_description for keyword in collaboration_keywords)
        
    async def process_task_queue(self):
        """Main task processing loop - should run continuously"""
        while True:
            try:
                # Get next task from priority queue
                priority, timestamp, task = await self.task_queue.get()
                
                # Select best available agent
                selected_agent = await self._select_best_agent(task)
                
                if not selected_agent:
                    # No agent available, requeue with delay
                    await asyncio.sleep(1)
                    await self.task_queue.put((priority, timestamp, task))
                    continue
                    
                # Execute task asynchronously
                asyncio.create_task(self._execute_task(task, selected_agent))
                
            except Exception as e:
                logging.error(f"Error in task queue processing: {e}")
                await asyncio.sleep(1)
                
    async def _execute_task(self, task: AgentTask, agent_id: str):
        """Execute a single task with the selected agent"""
        start_time = datetime.utcnow()
        
        try:
            # Mark task as active
            self.active_tasks[task.task_id] = {
                "agent_id": agent_id,
                "start_time": start_time,
                "task": task
            }
            self.agents[agent_id]["active_tasks"] += 1
            
            # Get agent instance and execute
            agent_instance = self.agents[agent_id]["instance"]
            
            # Set up timeout
            response = await asyncio.wait_for(
                agent_instance.execute_task(task),
                timeout=task.timeout_minutes * 60
            )
            
            # Calculate execution time
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            response.execution_time_ms = execution_time
            
            # Update agent metrics
            await self._update_agent_metrics(agent_id, response, task.capability)
            
            # Handle follow-up tasks
            if response.follow_up_tasks:
                for follow_up in response.follow_up_tasks:
                    follow_up.parent_task_id = task.task_id
                    await self.submit_task(follow_up)
                    
            # Update context store
            if response.context_updates:
                await self.context.update_context(task.task_id, response.context_updates)
                
            # Store completed result
            self.completed_tasks[task.task_id] = response
            
            logging.info(f"Task {task.task_id} completed by {agent_id} in {execution_time}ms")
            
        except asyncio.TimeoutError:
            # Handle timeout
            response = AgentResponse(
                task_id=task.task_id,
                agent_id=agent_id,
                success=False,
                output={"error": "Task timed out"},
                error_message=f"Task timed out after {task.timeout_minutes} minutes"
            )
            
            await self._handle_task_failure(task, agent_id, "timeout")
            
        except Exception as e:
            # Handle execution error
            response = AgentResponse(
                task_id=task.task_id,
                agent_id=agent_id,
                success=False,
                output={"error": str(e)},
                error_message=str(e)
            )
            
            await self._handle_task_failure(task, agent_id, str(e))
            
        finally:
            # Cleanup
            self.active_tasks.pop(task.task_id, None)
            if agent_id in self.agents:
                self.agents[agent_id]["active_tasks"] -= 1
                
    async def _select_best_agent(self, task: AgentTask) -> Optional[str]:
        """Select the best available agent for the task"""
        # Find agents with required capability
        capable_agents = [
            agent_id for agent_id, agent_info in self.agents.items()
            if task.capability in agent_info["capabilities"]
            and agent_info["active_tasks"] < agent_info["max_concurrent"]
        ]
        
        if not capable_agents:
            return None
            
        # Score agents based on multiple factors
        agent_scores = {}
        
        for agent_id in capable_agents:
            agent_info = self.agents[agent_id]
            metrics = self.agent_metrics[agent_id]
            
            # Load factor (prefer less busy agents)
            load_factor = 1.0 - (agent_info["active_tasks"] / agent_info["max_concurrent"])
            
            # Success rate factor
            success_rate = agent_info["success_rate"]
            
            # Speed factor (prefer faster agents for high priority)
            speed_factor = max(0.1, 1.0 - (agent_info["avg_execution_time"] / 30000))  # 30s baseline
            
            # Recency factor (prefer recently used agents for consistency)
            time_since_used = (datetime.utcnow() - agent_info["last_used"]).total_seconds()
            recency_factor = max(0.1, 1.0 - (time_since_used / 3600))  # 1 hour decay
            
            # Capability-specific performance
            cap_performance = metrics["capability_performance"].get(task.capability.value, 0.8)
            
            # Weight factors based on task priority
            if task.priority <= 2:  # High priority
                score = (success_rate * 0.4 + speed_factor * 0.3 + 
                        cap_performance * 0.2 + load_factor * 0.1)
            else:  # Normal priority
                score = (success_rate * 0.3 + load_factor * 0.3 + 
                        cap_performance * 0.2 + speed_factor * 0.1 + recency_factor * 0.1)
                
            agent_scores[agent_id] = score
            
        # Select highest scoring agent
        best_agent = max(agent_scores, key=agent_scores.get)
        self.agents[best_agent]["last_used"] = datetime.utcnow()
        
        return best_agent
        
    async def _update_agent_metrics(self, agent_id: str, response: AgentResponse, capability: AgentCapability):
        """Update performance metrics for an agent"""
        metrics = self.agent_metrics[agent_id]
        agent_info = self.agents[agent_id]
        
        # Update basic counters
        if response.success:
            metrics["tasks_completed"] += 1
        else:
            metrics["tasks_failed"] += 1
            
        agent_info["total_tasks"] += 1
        
        # Update success rate
        total_tasks = metrics["tasks_completed"] + metrics["tasks_failed"]
        agent_info["success_rate"] = metrics["tasks_completed"] / total_tasks
        
        # Update average execution time
        total_time = metrics["total_execution_time"] + response.execution_time_ms
        metrics["total_execution_time"] = total_time
        agent_info["avg_execution_time"] = total_time / total_tasks
        
        # Update capability-specific performance
        if capability.value not in metrics["capability_performance"]:
            metrics["capability_performance"][capability.value] = response.confidence
        else:
            # Exponential moving average
            current = metrics["capability_performance"][capability.value]
            metrics["capability_performance"][capability.value] = (
                0.7 * current + 0.3 * response.confidence
            )
            
        # Update average confidence
        if response.success:
            metrics["avg_confidence"] = (
                0.8 * metrics["avg_confidence"] + 0.2 * response.confidence
            )

class MultiAgentCoordinator:
    """Handles complex tasks requiring collaboration between multiple agents"""
    
    def __init__(self, orchestrator: AgentOrchestrator):
        self.orchestrator = orchestrator
        
    async def handle_collaborative_task(self, task: AgentTask) -> str:
        """Coordinate multiple agents for complex tasks"""
        logging.info(f"Handling collaborative task {task.task_id}")
        
        # Decompose task into subtasks
        subtasks = await self._decompose_task(task)
        
        if not subtasks:
            # Fallback to single agent if decomposition fails
            await self.orchestrator.task_queue.put((task.priority, task.created_at.timestamp(), task))
            return task.task_id
            
        # Create execution plan with dependencies
        execution_plan = self._create_execution_plan(subtasks)
        
        # Execute plan
        await self._execute_collaborative_plan(task.task_id, execution_plan)
        
        return task.task_id
        
    async def _decompose_task(self, task: AgentTask) -> List[AgentTask]:
        """Break down complex task into specialized subtasks"""
        decomposition_prompt = f"""
        You are a development task planner. Break down this complex development task into specific subtasks that can be handled by specialized AI agents.

        Original Task:
        Capability: {task.capability.value}
        Description: {task.input_data.get('description', 'No description')}
        Requirements: {task.input_data.get('requirements', 'No requirements')}
        Context: {json.dumps(task.context, indent=2)}

        Available Agent Capabilities:
        - code_review: Review code for quality, security, performance
        - code_generation: Generate new code from requirements
        - documentation: Create technical documentation
        - security_analysis: Analyze code for security vulnerabilities
        - testing: Generate and run tests
        - debugging: Find and fix bugs in code
        - infrastructure: Design deployment and infrastructure
        - architecture_design: Design system architecture
        - api_design: Design APIs and interfaces
        - database_design: Design database schemas

        For each subtask, provide:
        1. capability: Which agent capability is needed
        2. description: Clear description of the subtask
        3. input_data: Specific input data for this subtask
        4. priority: Priority level (1=highest, 5=lowest)
        5. dependencies: List of other subtask IDs this depends on

        Return as JSON array of subtasks. If the task cannot be meaningfully decomposed, return an empty array.
        """
        
        try:
            # Use the router to call a planning model
            response = await self.orchestrator.router.chat_completions({
                "model": "claude-3-5-sonnet",  # Use a capable model for planning
                "messages": [{"role": "user", "content": decomposition_prompt}],
                "temperature": 0.1,
                "max_tokens": 2000,
                "metadata": {"domain": "task_planning", "task_id": task.task_id}
            })
            
            # Parse the response
            content = response["choices"][0]["message"]["content"]
            
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                subtasks_data = json.loads(json_match.group())
            else:
                return []  # No valid JSON found
                
            # Convert to AgentTask objects
            subtasks = []
            for i, subtask_data in enumerate(subtasks_data):
                if not subtask_data.get("capability") or not subtask_data.get("description"):
                    continue
                    
                try:
                    capability = AgentCapability(subtask_data["capability"])
                except ValueError:
                    continue  # Skip invalid capabilities
                    
                subtask = AgentTask(
                    task_id=f"{task.task_id}_sub_{i}",
                    requester_id=task.requester_id,
                    capability=capability,
                    input_data={
                        "description": subtask_data["description"],
                        "parent_task": task.task_id,
                        **subtask_data.get("input_data", {})
                    },
                    context=task.context,
                    priority=subtask_data.get("priority", task.priority),
                    parent_task_id=task.task_id,
                    dependencies=subtask_data.get("dependencies", [])
                )
                subtasks.append(subtask)
                
            logging.info(f"Decomposed task {task.task_id} into {len(subtasks)} subtasks")
            return subtasks
            
        except Exception as e:
            logging.error(f"Failed to decompose task {task.task_id}: {e}")
            return []
            
    def _create_execution_plan(self, subtasks: List[AgentTask]) -> Dict[str, Any]:
        """Create execution plan with proper dependency ordering"""
        # Build dependency graph
        task_map = {task.task_id: task for task in subtasks}
        
        # Topological sort for execution order
        execution_order = self._topological_sort(subtasks)
        
        return {
            "tasks": task_map,
            "execution_order": execution_order,
            "parallel_groups": self._identify_parallel_groups(subtasks)
        }
        
    def _topological_sort(self, tasks: List[AgentTask]) -> List[str]:
        """Sort tasks by dependencies using topological sort"""
        # Simple topological sort implementation
        in_degree = {}
        graph = {}
        
        # Initialize
        for task in tasks:
            in_degree[task.task_id] = 0
            graph[task.task_id] = []
            
        # Build graph
        for task in tasks:
            for dep in task.dependencies:
                if dep in graph:
                    graph[dep].append(task.task_id)
                    in_degree[task.task_id] += 1
                    
        # Topological sort
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        return result
        
    def _identify_parallel_groups(self, tasks: List[AgentTask]) -> List[List[str]]:
        """Identify groups of tasks that can be executed in parallel"""
        # Group tasks by their dependency level
        levels = {}
        
        def get_level(task_id, task_map, memo={}):
            if task_id in memo:
                return memo[task_id]
                
            task = task_map.get(task_id)
            if not task or not task.dependencies:
                memo[task_id] = 0
                return 0
                
            max_dep_level = max(get_level(dep, task_map, memo) for dep in task.dependencies if dep in task_map)
            memo[task_id] = max_dep_level + 1
            return max_dep_level + 1
            
        task_map = {task.task_id: task for task in tasks}
        
        for task in tasks:
            level = get_level(task.task_id, task_map)
            if level not in levels:
                levels[level] = []
            levels[level].append(task.task_id)
            
        return [group for level, group in sorted(levels.items())]
        
    async def _execute_collaborative_plan(self, parent_task_id: str, plan: Dict[str, Any]):
        """Execute the collaborative task plan"""
        parallel_groups = plan["parallel_groups"]
        task_map = plan["tasks"]
        
        # Execute groups in sequence, tasks within groups in parallel
        for group in parallel_groups:
            # Submit all tasks in this group
            group_futures = []
            for task_id in group:
                task = task_map[task_id]
                future = asyncio.create_task(self._execute_subtask(task))
                group_futures.append((task_id, future))
                
            # Wait for all tasks in group to complete
            group_results = {}
            for task_id, future in group_futures:
                try:
                    result = await future
                    group_results[task_id] = result
                except Exception as e:
                    logging.error(f"Subtask {task_id} failed: {e}")
                    group_results[task_id] = None
                    
            # Update context with group results for next group
            await self.orchestrator.context.update_context(
                parent_task_id, 
                {"subtask_results": group_results}
            )
            
    async def _execute_subtask(self, subtask: AgentTask) -> Optional[AgentResponse]:
        """Execute a single subtask"""
        # Submit to orchestrator and wait for result
        task_id = await self.orchestrator.submit_task(subtask)
        return await self.orchestrator.get_task_result(task_id, timeout=subtask.timeout_minutes * 60)
```

---

## 2) Specialized Agent Implementations

### Code Agent

**`/platform/agents/specialized/code_agent.py`**
```python
import json
import re
from typing import Dict, Any, List
from datetime import datetime

from ..orchestrator import AgentCapability, AgentTask, AgentResponse

class CodeAgent:
    """Specialized agent for code-related tasks"""
    
    def __init__(self, router_client, context_store):
        self.router = router_client
        self.context = context_store
        self.capabilities = [
            AgentCapability.CODE_REVIEW,
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING,
            AgentCapability.PERFORMANCE_OPTIMIZATION
        ]
        self.max_concurrent = 5
        
    async def execute_task(self, task: AgentTask) -> AgentResponse:
        """Execute code-related task"""
        start_time = datetime.utcnow()
        
        try:
            if task.capability == AgentCapability.CODE_REVIEW:
                result = await self._perform_code_review(task)
            elif task.capability == AgentCapability.CODE_GENERATION:
                result = await self._generate_code(task)
            elif task.capability == AgentCapability.DEBUGGING:
                result = await self._debug_code(task)
            elif task.capability == AgentCapability.PERFORMANCE_OPTIMIZATION:
                result = await self._optimize_performance(task)
            else:
                raise ValueError(f"Unsupported capability: {task.capability}")
                
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return AgentResponse(
                task_id=task.task_id,
                agent_id="code_agent",
                success=True,
                output=result,
                confidence=result.get("confidence", 0.8),
                execution_time_ms=execution_time,
                follow_up_tasks=result.get("follow_up_tasks", [])
            )
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return AgentResponse(
                task_id=task.task_id,
                agent_id="code_agent",
                success=False,
                output={"error": str(e)},
                confidence=0.0,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
            
    async def _perform_code_review(self, task: AgentTask) -> Dict[str, Any]:
        """Perform comprehensive code review"""
        code = task.input_data.get("code", "")
        language = task.input_data.get("language", "python")
        context = task.input_data.get("context", "")
        
        review_prompt = f"""
        Perform a comprehensive code review of the following {language} code:
        
        Context: {context}
        
        ```{language}
        {code}
        ```
        
        Provide a detailed review covering:
        1. Code quality and best practices
        2. Security vulnerabilities
        3. Performance issues
        4. Maintainability concerns
        5. Suggested improvements with specific examples
        6. Overall assessment score (0-10)
        
        Format your response as JSON with the following structure:
        {{
            "overall_score": 8.5,
            "summary": "Brief overview of code quality",
            "issues": [
                {{
                    "type": "security|performance|style|logic",
                    "severity": "high|medium|low", 
                    "line": 23,
                    "message": "Issue description",
                    "suggestion": "How to fix it"
                }}
            ],
            "improvements": [
                {{
                    "category": "performance|readability|architecture",
                    "suggestion": "Specific improvement",
                    "example": "Code example if applicable"
                }}
            ],
            "positive_aspects": ["What was done well"],
            "confidence": 0.9
        }}
        """
        
        response = await self.router.chat_completions({
            "model": "claude-3-5-sonnet",  # Use capable model for code review
            "messages": [{"role": "user", "content": review_prompt}],
            "temperature": 0.1,
            "max_tokens": 2500,
            "metadata": {"domain": "code", "task_type": "review"}
        })
        
        try:
            # Parse JSON response
            content = response["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                review_result = json.loads(json_match.group())
            else:
                # Fallback to structured text parsing
                review_result = self._parse_text_review(content)
                
            # Determine if follow-up tasks are needed
            follow_ups = []
            high_severity_issues = [
                issue for issue in review_result.get("issues", [])
                if issue.get("severity") == "high"
            ]
            
            if high_severity_issues:
                # Create security analysis follow-up for security issues
                security_issues = [
                    issue for issue in high_severity_issues 
                    if issue.get("type") == "security"
                ]
                if security_issues:
                    follow_ups.append(AgentTask(
                        requester_id=task.requester_id,
                        capability=AgentCapability.SECURITY_ANALYSIS,
                        input_data={
                            "code": code,
                            "language": language,
                            "identified_issues": security_issues
                        },
                        context=task.context,
                        parent_task_id=task.task_id,
                        priority=2  # High priority for security
                    ))
            
            return {
                "review": review_result,
                "confidence": review_result.get("confidence", 0.8),
                "follow_up_tasks": follow_ups
            }
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return text response
            return {
                "review": {
                    "summary": response["choices"][0]["message"]["content"],
                    "overall_score": 7.0,
                    "confidence": 0.6
                },
                "confidence": 0.6
            }
            
    async def _generate_code(self, task: AgentTask) -> Dict[str, Any]:
        """Generate code based on requirements"""
        requirements = task.input_data.get("requirements", "")
        language = task.input_data.get("language", "python")
        style_guide = task.input_data.get("style_guide", "")
        existing_code = task.input_data.get("existing_code", "")
        
        # Get project context from context store
        context = await self.context.get_context(task.task_id)
        project_context = context.get("project", {})
        
        generation_prompt = f"""
        Generate {language} code based on the following requirements:
        
        Requirements:
        {requirements}
        
        Style Guide: {style_guide or "Follow standard conventions"}
        
        Project Context:
        - Architecture: {project_context.get('architecture', 'Not specified')}
        - Dependencies: {project_context.get('dependencies', [])}
        - Patterns: {project_context.get('patterns', [])}
        
        Existing Code Context:
        {existing_code}
        
        Provide:
        1. Complete, production-ready code
        2. Comprehensive docstrings/comments
        3. Error handling and edge cases
        4. Unit test suggestions
        5. Integration points with existing code
        
        Format as JSON:
        {{
            "code": "Complete code implementation",
            "explanation": "Detailed explanation of the implementation",
            "tests": "Suggested unit tests",
            "dependencies": ["Required packages/imports"],
            "integration_notes": "How this integrates with existing code",
            "confidence": 0.9
        }}
        """
        
        response = await self.router.chat_completions({
            "model": "claude-3-5-sonnet",
            "messages": [{"role": "user", "content": generation_prompt}],
            "temperature": 0.2,
            "max_tokens": 3000,
            "metadata": {"domain": "code", "task_type": "generation"}
        })
        
        try:
            content = response["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                code_result = json.loads(json_match.group())
            else:
                # Extract code blocks from response
                code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', content, re.DOTALL)
                code_result = {
                    "code": code_blocks[0] if code_blocks else content,
                    "explanation": "Generated code based on requirements",
                    "confidence": 0.7
                }
                
            # Create follow-up tasks if needed
            follow_ups = []
            if code_result.get("tests"):
                follow_ups.append(AgentTask(
                    requester_id=task.requester_id,
                    capability=AgentCapability.TESTING,
                    input_data={
                        "code": code_result["code"],
                        "test_suggestions": code_result["tests"],
                        "language": language
                    },
                    context=task.context,
                    parent_task_id=task.task_id,
                    priority=task.priority + 1
                ))
                
            return {
                "generated_code": code_result,
                "confidence": code_result.get("confidence", 0.8),
                "follow_up_tasks": follow_ups
            }
            
        except json.JSONDecodeError:
            return {
                "generated_code": {
                    "code": response["choices"][0]["message"]["content"],
                    "explanation": "Code generation completed",
                    "confidence": 0.7
                },
                "confidence": 0.7
            }

    async def _debug_code(self, task: AgentTask) -> Dict[str, Any]:
        """Debug code issues and provide fixes"""
        code = task.input_data.get("code", "")
        error_message = task.input_data.get("error_message", "")
        language = task.input_data.get("language", "python")
        reproduction_steps = task.input_data.get("reproduction_steps", "")
        
        debug_prompt = f"""
        Debug the following {language} code that is experiencing issues:
        
        Code:
        ```{language}
        {code}
        ```
        
        Error Message: {error_message}
        
        Reproduction Steps: {reproduction_steps}
        
        Provide:
        1. Root cause analysis
        2. Specific fixes with corrected code
        3. Prevention strategies
        4. Testing approach to verify the fix
        
        Format as JSON:
        {{
            "root_cause": "Detailed explanation of the issue",
            "fixes": [
                {{
                    "description": "What this fix addresses",
                    "fixed_code": "Corrected code",
                    "explanation": "Why this fix works"
                }}
            ],
            "prevention": "How to prevent similar issues",
            "test_strategy": "How to test the fix",
            "confidence": 0.9
        }}
        """
        
        response = await self.router.chat_completions({
            "model": "claude-3-5-sonnet",
            "messages": [{"role": "user", "content": debug_prompt}],
            "temperature": 0.1,
            "max_tokens": 2000,
            "metadata": {"domain": "code", "task_type": "debugging"}
        })
        
        try:
            content = response["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                debug_result = json.loads(json_match.group())
            else:
                debug_result = {
                    "root_cause": "Analysis provided in text format",
                    "fixes": [{"description": "See detailed response", "fixed_code": "", "explanation": content}],
                    "confidence": 0.6
                }
                
            return {
                "debug_analysis": debug_result,
                "confidence": debug_result.get("confidence", 0.8)
            }
            
        except json.JSONDecodeError:
            return {
                "debug_analysis": {
                    "root_cause": response["choices"][0]["message"]["content"],
                    "confidence": 0.6
                },
                "confidence": 0.6
            }

    async def _optimize_performance(self, task: AgentTask) -> Dict[str, Any]:
        """Optimize code for better performance"""
        code = task.input_data.get("code", "")
        language = task.input_data.get("language", "python")
        performance_metrics = task.input_data.get("current_metrics", {})
        
        optimization_prompt = f"""
        Analyze and optimize the following {language} code for performance:
        
        Current Code:
        ```{language}
        {code}
        ```
        
        Current Performance Metrics: {json.dumps(performance_metrics, indent=2)}
        
        Provide:
        1. Performance analysis of current code
        2. Specific optimization suggestions
        3. Optimized code with improvements
        4. Expected performance gains
        5. Trade-offs and considerations
        
        Format as JSON:
        {{
            "analysis": "Performance bottlenecks and issues",
            "optimizations": [
                {{
                    "type": "algorithmic|memory|io|caching",
                    "description": "What optimization was applied",
                    "before_code": "Original problematic code",
                    "after_code": "Optimized code",
                    "expected_gain": "Expected improvement"
                }}
            ],
            "optimized_code": "Complete optimized version",
            "trade_offs": "Any trade-offs or considerations",
            "confidence": 0.85
        }}
        """
        
        response = await self.router.chat_completions({
            "model": "claude-3-5-sonnet",
            "messages": [{"role": "user", "content": optimization_prompt}],
            "temperature": 0.1,
            "max_tokens": 2500,
            "metadata": {"domain": "code", "task_type": "optimization"}
        })
        
        try:
            content = response["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                optimization_result = json.loads(json_match.group())
            else:
                optimization_result = {
                    "analysis": content,
                    "optimizations": [],
                    "confidence": 0.6
                }
                
            return {
                "optimization_analysis": optimization_result,
                "confidence": optimization_result.get("confidence", 0.7)
            }
            
        except json.JSONDecodeError:
            return {
                "optimization_analysis": {
                    "analysis": response["choices"][0]["message"]["content"],
                    "confidence": 0.6
                },
                "confidence": 0.6
            }

    def _parse_text_review(self, content: str) -> Dict[str, Any]:
        """Parse text-based code review into structured format"""
        # Simple fallback parsing for when JSON parsing fails
        lines = content.split('\n')
        issues = []
        improvements = []
        
        current_section = None
        for line in lines:
            line = line.strip()
            if 'security' in line.lower() or 'vulnerability' in line.lower():
                issues.append({
                    "type": "security",
                    "severity": "high" if 'critical' in line.lower() else "medium",
                    "message": line,
                    "suggestion": "Review security implications"
                })
            elif 'performance' in line.lower():
                issues.append({
                    "type": "performance", 
                    "severity": "medium",
                    "message": line,
                    "suggestion": "Optimize for better performance"
                })
                
        return {
            "summary": "Code review completed",
            "overall_score": 7.5,
            "issues": issues,
            "improvements": improvements,
            "confidence": 0.6
        }

class SecurityAgent:
    """Specialized agent for security analysis"""
    
    def __init__(self, router_client, vulnerability_db=None):
        self.router = router_client
        self.vulnerability_db = vulnerability_db
        self.capabilities = [AgentCapability.SECURITY_ANALYSIS]
        self.max_concurrent = 3
        
    async def execute_task(self, task: AgentTask) -> AgentResponse:
        """Execute security analysis task"""
        start_time = datetime.utcnow()
        
        try:
            result = await self._analyze_security(task)
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return AgentResponse(
                task_id=task.task_id,
                agent_id="security_agent",
                success=True,
                output=result,
                confidence=result.get("confidence", 0.9),
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return AgentResponse(
                task_id=task.task_id,
                agent_id="security_agent",
                success=False,
                output={"error": str(e)},
                confidence=0.0,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
            
    async def _analyze_security(self, task: AgentTask) -> Dict[str, Any]:
        """Perform comprehensive security analysis"""
        code = task.input_data.get("code", "")
        language = task.input_data.get("language", "python")
        dependencies = task.input_data.get("dependencies", [])
        
        # Static analysis for common patterns
        static_analysis = await self._static_security_analysis(code, language)
        
        # LLM-based security review
        llm_analysis = await self._llm_security_review(code, language)
        
        # Dependency vulnerability check
        dependency_analysis = await self._check_dependencies(dependencies)
        
        # Combine analyses
        combined_analysis = {
            "static_analysis": static_analysis,
            "llm_analysis": llm_analysis,
            "dependency_analysis": dependency_analysis,
            "overall_risk_score": self._calculate_risk_score(static_analysis, llm_analysis, dependency_analysis),
            "recommendations": self._generate_security_recommendations(static_analysis, llm_analysis)
        }
        
        return {
            "security_analysis": combined_analysis,
            "confidence": 0.9
        }
        
    async def _static_security_analysis(self, code: str, language: str) -> Dict[str, Any]:
        """Perform static analysis for common security patterns"""
        issues = []
        
        # Language-specific security patterns
        if language.lower() == "python":
            patterns = {
                "sql_injection": [r".*\.execute\s*\(\s*['\"].*%.*['\"]", r".*\.execute\s*\(\s*.*\+.*\)"],
                "command_injection": [r"os\.system\s*\(.*\+", r"subprocess\.call\s*\(.*\+"],
                "hardcoded_secrets": [r"password\s*=\s*['\"][^'\"]+['\"]", r"api_key\s*=\s*['\"][^'\"]+['\"]"],
                "unsafe_deserialization": [r"pickle\.loads", r"yaml\.load\(", r"eval\s*\("],
                "path_traversal": [r"\.\.\/", r"\.\.\\\"]
            }
        elif language.lower() in ["javascript", "typescript"]:
            patterns = {
                "xss": [r"innerHTML\s*=.*\+", r"document\.write\s*\(.*\+"],
                "prototype_pollution": [r"__proto__", r"constructor\.prototype"],
                "unsafe_eval": [r"eval\s*\(", r"new\s+Function\s*\("],
                "hardcoded_secrets": [r"password\s*:\s*['\"][^'\"]+['\"]", r"apiKey\s*:\s*['\"][^'\"]+['\"]"]
            }
        else:
            patterns = {
                "hardcoded_secrets": [r"password.*=.*['\"][^'\"]+['\"]", r"secret.*=.*['\"][^'\"]+['\"]"]
            }
            
        for issue_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    issues.append({
                        "type": issue_type,
                        "severity": "high" if issue_type in ["sql_injection", "command_injection"] else "medium",
                        "line": line_num,
                        "pattern": pattern,
                        "match": match.group()
                    })
                    
        return {
            "issues_found": len(issues),
            "issues": issues,
            "scan_coverage": f"static_patterns_{language}"
        }
        
    async def _llm_security_review(self, code: str, language: str) -> Dict[str, Any]:
        """Use LLM for advanced security analysis"""
        security_prompt = f"""
        Perform a comprehensive security analysis of this {language} code:
        
        ```{language}
        {code}
        ```
        
        Analyze for:
        1. Injection vulnerabilities (SQL, Command, XSS, etc.)
        2. Authentication and authorization flaws
        3. Data exposure risks
        4. Cryptographic issues
        5. Input validation problems
        6. Business logic vulnerabilities
        7. Configuration and deployment security
        
        For each vulnerability found, provide:
        - Severity level (Critical/High/Medium/Low)
        - Specific line numbers if applicable
        - Detailed explanation
        - Remediation steps
        - OWASP category if applicable
        
        Format as JSON:
        {{
            "vulnerabilities": [
                {{
                    "id": "unique_id",
                    "type": "vulnerability_type",
                    "severity": "Critical|High|Medium|Low",
                    "line": 42,
                    "title": "Brief description",
                    "description": "Detailed explanation",
                    "remediation": "How to fix it",
                    "owasp_category": "A01:2021 – Broken Access Control",
                    "cwe": "CWE-89"
                }}
            ],
            "overall_assessment": "Summary of security posture",
            "confidence": 0.9
        }}
        """
        
        response = await self.router.chat_completions({
            "model": "claude-3-5-sonnet",
            "messages": [{"role": "user", "content": security_prompt}],
            "temperature": 0.1,
            "max_tokens": 3000,
            "metadata": {"domain": "security", "task_type": "analysis"}
        })
        
        try:
            content = response["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                security_result = json.loads(json_match.group())
            else:
                security_result = {
                    "vulnerabilities": [],
                    "overall_assessment": content,
                    "confidence": 0.6
                }
                
            return security_result
            
        except json.JSONDecodeError:
            return {
                "vulnerabilities": [],
                "overall_assessment": response["choices"][0]["message"]["content"],
                "confidence": 0.6
            }
            
    async def _check_dependencies(self, dependencies: List[str]) -> Dict[str, Any]:
        """Check dependencies for known vulnerabilities"""
        # This would integrate with vulnerability databases like NIST NVD, Snyk, etc.
        vulnerable_deps = []
        
        # Placeholder implementation - would integrate with real vulnerability DB
        known_vulnerable = {
            "requests": {"versions": ["<2.20.0"], "cve": "CVE-2018-18074"},
            "django": {"versions": ["<2.2.13"], "cve": "CVE-2020-13254"},
            "express": {"versions": ["<4.17.1"], "cve": "CVE-2019-5413"}
        }
        
        for dep in dependencies:
            dep_name = dep.split("==")[0].split(">=")[0].split("<=")[0]
            if dep_name in known_vulnerable:
                vulnerable_deps.append({
                    "name": dep_name,
                    "current_version": dep,
                    "vulnerability": known_vulnerable[dep_name]
                })
                
        return {
            "total_dependencies": len(dependencies),
            "vulnerable_dependencies": len(vulnerable_deps),
            "vulnerabilities": vulnerable_deps
        }
        
    def _calculate_risk_score(self, static: Dict, llm: Dict, deps: Dict) -> float:
        """Calculate overall security risk score (0-10, higher is worse)"""
        score = 0.0
        
        # Static analysis contribution
        static_issues = static.get("issues", [])
        high_severity_static = len([i for i in static_issues if i.get("severity") == "high"])
        score += high_severity_static * 2.0
        score += (len(static_issues) - high_severity_static) * 1.0
        
        # LLM analysis contribution
        llm_vulns = llm.get("vulnerabilities", [])
        critical_vulns = len([v for v in llm_vulns if v.get("severity") == "Critical"])
        high_vulns = len([v for v in llm_vulns if v.get("severity") == "High"])
        score += critical_vulns * 3.0
        score += high_vulns * 2.0
        
        # Dependency contribution
        vulnerable_deps = deps.get("vulnerable_dependencies", 0)
        score += vulnerable_deps * 1.5
        
        return min(10.0, score)
        
    def _generate_security_recommendations(self, static: Dict, llm: Dict) -> List[str]:
        """Generate prioritized security recommendations"""
        recommendations = []
        
        # High priority recommendations based on findings
        static_issues = static.get("issues", [])
        high_severity = [i for i in static_issues if i.get("severity") == "high"]
        
        if high_severity:
            recommendations.append(
                f"URGENT: Address {len(high_severity)} high-severity security issues found in static analysis"
            )
            
        llm_critical = [v for v in llm.get("vulnerabilities", []) if v.get("severity") == "Critical"]
        if llm_critical:
            recommendations.append(
                f"CRITICAL: Fix {len(llm_critical)} critical vulnerabilities identified in code review"
            )
            
        # General recommendations
        if any("sql_injection" in i.get("type", "") for i in static_issues):
            recommendations.append("Implement parameterized queries to prevent SQL injection")
            
        if any("hardcoded_secrets" in i.get("type", "") for i in static_issues):
            recommendations.append("Move hardcoded secrets to environment variables or secure vault")
            
        recommendations.extend([
            "Implement comprehensive input validation",
            "Add security headers to prevent common attacks",
            "Regular security dependency updates",
            "Implement proper error handling to prevent information disclosure"
        ])
        
        return recommendations[:8]  # Limit to most important recommendations
```

---

## 3) Workflow Automation Engine

**`/platform/workflows/engine.py`**
```python
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import logging
from datetime import datetime, timedelta
import croniter
import uuid

class TriggerType(Enum):
    GIT_PUSH = "git_push"
    GIT_PR = "git_pr"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    MANUAL = "manual"
    TASK_COMPLETION = "task_completion"
    INTEGRATION_EVENT = "integration_event"

class ActionType(Enum):
    AI_AGENT_TASK = "ai_agent_task"
    CODE_REVIEW = "code_review"
    RUN_TESTS = "run_tests"
    DEPLOY = "deploy"
    GENERATE_DOCS = "generate_docs"
    SECURITY_SCAN = "security_scan"
    NOTIFY = "notify"
    CREATE_ISSUE = "create_issue"
    INTEGRATION_ACTION = "integration_action"

@dataclass
class WorkflowTrigger:
    trigger_type: TriggerType
    config: Dict[str, Any]
    conditions: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class WorkflowAction:
    action_id: str
    action_type: ActionType
    config: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    timeout_minutes: int = 30
    retry_count: int = 2
    condition: Optional[str] = None  # Expression to evaluate for conditional execution

@dataclass
class Workflow:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    triggers: List[WorkflowTrigger] = field(default_factory=list)
    actions: List[WorkflowAction] = field(default_factory=list)
    enabled: bool = True
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)

@dataclass
class WorkflowInstance:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    status: str = "pending"  # pending, running, completed, failed, cancelled
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    action_results: Dict[str, Any] = field(default_factory=dict)
    current_action: Optional[str] = None
    error_message: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

class WorkflowEngine:
    """Event-driven workflow automation engine"""
    
    def __init__(self, agent_orchestrator, integration_hub):
        self.orchestrator = agent_orchestrator
        self.integrations = integration_hub
        
        # Workflow registry
        self.workflows: Dict[str, Workflow] = {}
        self.workflow_instances: Dict[str, WorkflowInstance] = {}
        
        # Event handling
        self.event_handlers: Dict[TriggerType, Callable] = {}
        self.scheduled_workflows: Dict[str, Dict] = {}
        
        # Performance tracking
        self.execution_metrics: Dict[str, Any] = {}
        
        self._setup_event_handlers()
        
    def _setup_event_handlers(self):
        """Set up event handlers for different trigger types"""
        self.event_handlers = {
            TriggerType.GIT_PUSH: self._handle_git_push,
            TriggerType.GIT_PR: self._handle_git_pr,
            TriggerType.WEBHOOK: self._handle_webhook,
            TriggerType.TASK_COMPLETION: self._handle_task_completion,
            TriggerType.INTEGRATION_EVENT: self._handle_integration_event
        }
        
    async def register_workflow(self, workflow: Workflow) -> str:
        """Register a workflow and set up its triggers"""
        self.workflows[workflow.id] = workflow
        
        # Set up triggers
        for trigger in workflow.triggers:
            await self._setup_trigger(workflow.id, trigger)
            
        logging.info(f"Registered workflow: {workflow.name} ({workflow.id})")
        return workflow.id
        
    async def _setup_trigger(self, workflow_id: str, trigger: WorkflowTrigger):
        """Set up trigger monitoring"""
        if trigger.trigger_type == TriggerType.SCHEDULE:
            # Set up scheduled execution
            cron_expr = trigger.config.get("cron", "0 0 * * *")
            timezone = trigger.config.get("timezone", "UTC")
            
            try:
                cron = croniter.croniter(cron_expr, datetime.now())
                self.scheduled_workflows[f"{workflow_id}_{trigger.trigger_type.value}"] = {
                    "workflow_id": workflow_id,
                    "cron": cron,
                    "next_run": cron.get_next(datetime),
                    "config": trigger.config
                }
                logging.info(f"Scheduled workflow {workflow_id} with cron: {cron_expr}")
            except Exception as e:
                logging.error(f"Invalid cron expression for workflow {workflow_id}: {e}")
                
        elif trigger.trigger_type in [TriggerType.GIT_PUSH, TriggerType.GIT_PR]:
            # Register with integration hub for Git events
            await self._register_git_webhook(workflow_id, trigger)
            
    async def _register_git_webhook(self, workflow_id: str, trigger: WorkflowTrigger):
        """Register webhook for Git events"""
        git_integration = await self.integrations.get_integration("github")
        if git_integration:
            event_type = "push" if trigger.trigger_type == TriggerType.GIT_PUSH else "pull_request"
            repository = trigger.config.get("repository")
            
            if repository:
                await git_integration.register_webhook(
                    workflow_id=workflow_id,
                    event_type=event_type,
                    repository=repository,
                    config=trigger.config
                )
                
    async def trigger_workflow(self, workflow_id: str, trigger_data: Dict[str, Any] = None) -> str:
        """Manually trigger a workflow execution"""
        workflow = self.workflows.get(workflow_id)
        if not workflow or not workflow.enabled:
            raise ValueError(f"Workflow {workflow_id} not found or disabled")
            
        instance = WorkflowInstance(
            workflow_id=workflow_id,
            status="pending",
            trigger_data=trigger_data or {},
            context={"manual_trigger": True, "triggered_at": datetime.utcnow().isoformat()}
        )
        
        self.workflow_instances[instance.id] = instance
        
        # Start execution asynchronously
        asyncio.create_task(self._execute_workflow(instance))
        
        logging.info(f"Triggered workflow {workflow.name} - instance {instance.id}")
        return instance.id
        
    async def handle_external_event(self, event_type: str, event_data: Dict[str, Any]):
        """Handle external events that might trigger workflows"""
        trigger_type = None
        
        # Map event types to trigger types
        if event_type in ["push", "pull_request"]:
            trigger_type = TriggerType.GIT_PUSH if event_type == "push" else TriggerType.GIT_PR
        elif event_type.startswith("webhook_"):
            trigger_type = TriggerType.WEBHOOK
        elif event_type.startswith("integration_"):
            trigger_type = TriggerType.INTEGRATION_EVENT
            
        if trigger_type and trigger_type in self.event_handlers:
            await self.event_handlers[trigger_type](event_data)
            
    async def _handle_git_push(self, event_data: Dict[str, Any]):
        """Handle Git push events"""
        repository = event_data.get("repository", {}).get("full_name")
        branch = event_data.get("ref", "").replace("refs/heads/", "")
        
        # Find workflows triggered by this push
        for workflow_id, workflow in self.workflows.items():
            if not workflow.enabled:
                continue
                
            for trigger in workflow.triggers:
                if trigger.trigger_type != TriggerType.GIT_PUSH:
                    continue
                    
                # Check if this push matches the trigger conditions
                trigger_repo = trigger.config.get("repository")
                trigger_branches = trigger.config.get("branches", ["main", "master"])
                
                if trigger_repo == repository and branch in trigger_branches:
                    # Additional condition checking
                    if await self._evaluate_trigger_conditions(trigger, event_data):
                        await self.trigger_workflow(workflow_id, event_data)
                        
    async def _handle_git_pr(self, event_data: Dict[str, Any]):
        """Handle Git pull request events"""
        action = event_data.get("action")
        repository = event_data.get("repository", {}).get("full_name")
        pr_data = event_data.get("pull_request", {})
        
        # Find workflows triggered by this PR event
        for workflow_id, workflow in self.workflows.items():
            if not workflow.enabled:
                continue
                
            for trigger in workflow.triggers:
                if trigger.trigger_type != TriggerType.GIT_PR:
                    continue
                    
                trigger_repo = trigger.config.get("repository")
                trigger_actions = trigger.config.get("actions", ["opened", "synchronize"])
                
                if trigger_repo == repository and action in trigger_actions:
                    # Enrich event data with PR details
                    enriched_data = {
                        **event_data,
                        "pr": {
                            "title": pr_data.get("title"),
                            "body": pr_data.get("body"),
                            "diff_url": pr_data.get("diff_url"),
                            "base_branch": pr_data.get("base", {}).get("ref"),
                            "head_branch": pr_data.get("head", {}).get("ref"),
                            "files_changed": pr_data.get("changed_files", 0),
                            "additions": pr_data.get("additions", 0),
                            "deletions": pr_data.get("deletions", 0)
                        }
                    }
                    
                    if await self._evaluate_trigger_conditions(trigger, enriched_data):
                        await self.trigger_workflow(workflow_id, enriched_data)
                        
    async def _evaluate_trigger_conditions(self, trigger: WorkflowTrigger, event_data: Dict[str, Any]) -> bool:
        """Evaluate trigger conditions to determine if workflow should run"""
        conditions = trigger.conditions
        if not conditions:
            return True
            
        # Simple condition evaluation - could be extended with expression parser
        for key, expected_value in conditions.items():
            actual_value = self._get_nested_value(event_data, key)
            
            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            elif actual_value != expected_value:
                return False
                
        return True
        
    def _get_nested_value(self, data: Dict, key_path: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        keys = key_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
                
        return value
        
    async def _execute_workflow(self, instance: WorkflowInstance):
        """Execute a workflow instance"""
        workflow = self.workflows.get(instance.workflow_id)
        if not workflow:
            instance.status = "failed"
            instance.error_message = f"Workflow {instance.workflow_id} not found"
            return
            
        instance.status = "running"
        instance.start_time = datetime.utcnow()
        
        try:
            logging.info(f"Starting workflow execution: {workflow.name} (instance: {instance.id})")
            
            # Build execution plan
            execution_plan = self._build_execution_plan(workflow.actions)
            
            # Execute actions according to plan
            await self._execute_action_plan(instance, execution_plan)
            
            instance.status = "completed"
            instance.end_time = datetime.utcnow()
            
            logging.info(f"Workflow completed: {workflow.name} (instance: {instance.id})")
            
        except Exception as e:
            instance.status = "failed"
            instance.error_message = str(e)
            instance.end_time = datetime.utcnow()
            
            logging.error(f"Workflow failed: {workflow.name} (instance: {instance.id}) - {e}")
            
        finally:
            # Send completion notification
            await self._notify_workflow_completion(instance)
            
    def _build_execution_plan(self, actions: List[WorkflowAction]) -> Dict[str, Any]:
        """Build execution plan considering dependencies"""
        # Create dependency graph
        action_map = {action.action_id: action for action in actions}
        dependencies = {}
        
        for action in actions:
            dependencies[action.action_id] = action.depends_on.copy()
            
        # Topological sort to determine execution order
        execution_levels = []
        remaining_actions = set(action_map.keys())
        
        while remaining_actions:
            # Find actions with no unmet dependencies
            ready_actions = []
            for action_id in remaining_actions:
                deps = dependencies[action_id]
                if all(dep not in remaining_actions for dep in deps):
                    ready_actions.append(action_id)
                    
            if not ready_actions:
                # Circular dependency or other issue
                raise ValueError("Circular dependency detected in workflow actions")
                
            execution_levels.append(ready_actions)
            remaining_actions -= set(ready_actions)
            
        return {
            "action_map": action_map,
            "execution_levels": execution_levels
        }
        
    async def _execute_action_plan(self, instance: WorkflowInstance, plan: Dict[str, Any]):
        """Execute workflow actions according to plan"""
        action_map = plan["action_map"]
        execution_levels = plan["execution_levels"]
        
        for level, action_ids in enumerate(execution_levels):
            logging.info(f"Executing level {level} with actions: {action_ids}")
            
            # Execute all actions in this level concurrently
            level_tasks = []
            for action_id in action_ids:
                action = action_map[action_id]
                task = asyncio.create_task(self._execute_single_action(instance, action))
                level_tasks.append((action_id, task))
                
            # Wait for all actions in this level to complete
            for action_id, task in level_tasks:
                try:
                    result = await task
                    instance.action_results[action_id] = result
                    logging.info(f"Action {action_id} completed successfully")
                except Exception as e:
                    instance.action_results[action_id] = {"success": False, "error": str(e)}
                    logging.error(f"Action {action_id} failed: {e}")
                    
                    # Check if this is a critical failure
                    action = action_map[action_id]
                    if action.config.get("critical", False):
                        raise Exception(f"Critical action {action_id} failed: {e}")
                        
    async def _execute_single_action(self, instance: WorkflowInstance, action: WorkflowAction) -> Dict[str, Any]:
        """Execute a single workflow action"""
        instance.current_action = action.action_id
        start_time = datetime.utcnow()
        
        # Evaluate condition if present
        if action.condition and not self._evaluate_action_condition(action.condition, instance):
            return {"success": True, "skipped": True, "reason": "condition_not_met"}
            
        try:
            # Execute based on action type
            if action.action_type == ActionType.AI_AGENT_TASK:
                result = await self._execute_agent_task_action(instance, action)
            elif action.action_type == ActionType.CODE_REVIEW:
                result = await self._execute_code_review_action(instance, action)
            elif action.action_type == ActionType.SECURITY_SCAN:
                result = await self._execute_security_scan_action(instance, action)
            elif action.action_type == ActionType.NOTIFY:
                result = await self._execute_notification_action(instance, action)
            elif action.action_type == ActionType.INTEGRATION_ACTION:
                result = await self._execute_integration_action(instance, action)
            else:
                raise ValueError(f"Unsupported action type: {action.action_type}")
                
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result["execution_time_seconds"] = execution_time
            
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return {
                "success": False,
                "error": str(e),
                "execution_time_seconds": execution_time
            }
            
    def _evaluate_action_condition(self, condition: str, instance: WorkflowInstance) -> bool:
        """Evaluate action condition - simplified expression evaluation"""
        # This would be more sophisticated in practice
        # For now, support simple conditions like "trigger_data.action == 'opened'"
        try:
            # Replace template variables with actual values
            context = {
                "trigger_data": instance.trigger_data,
                "action_results": instance.action_results,
                "context": instance.context
            }
            
            # Simple evaluation - in production, use a proper expression parser
            return eval(condition, {"__builtins__": {}}, context)
        except:
            return True  # Default to execute if condition evaluation fails
            
    async def _execute_agent_task_action(self, instance: WorkflowInstance, action: WorkflowAction) -> Dict[str, Any]:
        """Execute AI agent task action"""
        config = action.config
        
        # Build input data with template substitution
        input_data = await self._substitute_templates(config.get("input", {}), instance)
        
        # Create agent task
        from ..agents.orchestrator import AgentTask, AgentCapability
        
        agent_task = AgentTask(
            requester_id=f"workflow_{instance.workflow_id}",
            capability=AgentCapability(config["capability"]),
            input_data=input_data,
            context={
                "workflow_instance": instance.id,
                "workflow_id": instance.workflow_id,
                "trigger_data": instance.trigger_data
            },
            priority=config.get("priority", 3)
        )
        
        # Submit to orchestrator and wait for result
        task_id = await self.orchestrator.submit_task(agent_task)
        result = await self.orchestrator.get_task_result(task_id, timeout=action.timeout_minutes * 60)
        
        if result and result.success:
            return {"success": True, "agent_result": result.output, "task_id": task_id}
        else:
            error_msg = result.error_message if result else "Task timed out or failed"
            return {"success": False, "error": error_msg, "task_id": task_id}
            
    async def _execute_code_review_action(self, instance: WorkflowInstance, action: WorkflowAction) -> Dict[str, Any]:
        """Execute code review action"""
        # Extract code from trigger data (e.g., from PR diff)
        trigger_data = instance.trigger_data
        
        if "pull_request" in trigger_data:
            # GitHub PR event
            diff_url = trigger_data["pull_request"].get("diff_url")
            if diff_url:
                # Fetch diff content
                code_diff = await self._fetch_pr_diff(diff_url)
            else:
                code_diff = "No diff available"
        else:
            code_diff = action.config.get("code", "No code provided")
            
        # Submit code review task
        from ..agents.orchestrator import AgentTask, AgentCapability
        
        review_task = AgentTask(
            requester_id=f"workflow_{instance.workflow_id}",
            capability=AgentCapability.CODE_REVIEW,
            input_data={
                "code": code_diff,
                "language": action.config.get("language", "python"),
                "context": trigger_data.get("pull_request", {}).get("title", "")
            },
            context={"workflow_instance": instance.id},
            priority=2  # Higher priority for code reviews
        )
        
        task_id = await self.orchestrator.submit_task(review_task)
        result = await self.orchestrator.get_task_result(task_id)
        
        if result and result.success:
            return {"success": True, "review_result": result.output}
        else:
            return {"success": False, "error": "Code review failed"}
            
    async def _execute_security_scan_action(self, instance: WorkflowInstance, action: WorkflowAction) -> Dict[str, Any]:
        """Execute security scan action"""
        config = action.config
        
        # Get code to scan
        code = await self._extract_code_from_trigger(instance.trigger_data, config)
        
        from ..agents.orchestrator import AgentTask, AgentCapability
        
        security_task = AgentTask(
            requester_id=f"workflow_{instance.workflow_id}",
            capability=AgentCapability.SECURITY_ANALYSIS,
            input_data={
                "code": code,
                "language": config.get("language", "python"),
                "include_dependencies": config.get("include_dependencies", True)
            },
            context={"workflow_instance": instance.id},
            priority=2
        )
        
        task_id = await self.orchestrator.submit_task(security_task)
        result = await self.orchestrator.get_task_result(task_id)
        
        if result and result.success:
            return {"success": True, "security_result": result.output}
        else:
            return {"success": False, "error": "Security scan failed"}
            
    async def _execute_notification_action(self, instance: WorkflowInstance, action: WorkflowAction) -> Dict[str, Any]:
        """Execute notification action"""
        config = action.config
        integration_type = config.get("integration", "slack")
        
        # Get integration
        integration = await self.integrations.get_integration(integration_type)
        if not integration:
            return {"success": False, "error": f"Integration {integration_type} not available"}
            
        # Prepare message with template substitution
        message = await self._substitute_templates(config.get("message", "Workflow notification"), instance)
        
        # Send notification
        try:
            if hasattr(integration, 'send_message'):
                result = await integration.send_message(
                    channel=config.get("channel", "#general"),
                    message=message
                )
                return {"success": True, "notification_result": result}
            else:
                return {"success": False, "error": "Integration does not support messaging"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _execute_integration_action(self, instance: WorkflowInstance, action: WorkflowAction) -> Dict[str, Any]:
        """Execute generic integration action"""
        config = action.config
        integration_type = config["integration"]
        integration_action = config["action"]
        
        # Get integration and execute action
        integration = await self.integrations.get_integration(integration_type)
        if not integration:
            return {"success": False, "error": f"Integration {integration_type} not available"}
            
        # Prepare parameters with template substitution
        params = await self._substitute_templates(config.get("parameters", {}), instance)
        
        try:
            result = await self.integrations.execute_integration_action(
                integration_type, integration_action, **params
            )
            return {"success": True, "integration_result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _substitute_templates(self, template_data: Any, instance: WorkflowInstance) -> Any:
        """Substitute template variables in data"""
        if isinstance(template_data, str):
            # Simple template substitution
            template = template_data
            
            # Available variables
            variables = {
                "trigger": instance.trigger_data,
                "action_results": instance.action_results,
                "context": instance.context,
                "workflow_id": instance.workflow_id,
                "instance_id": instance.id,
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "datetime": datetime.utcnow().isoformat()
            }
            
            # Simple string replacement (in production, use a proper template engine)
            for key, value in variables.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        template = template.replace(f"{{{{{key}.{sub_key}}}}}", str(sub_value))
                else:
                    template = template.replace(f"{{{{{key}}}}}", str(value))
                    
            return template
            
        elif isinstance(template_data, dict):
            return {k: await self._substitute_templates(v, instance) for k, v in template_data.items()}
        elif isinstance(template_data, list):
            return [await self._substitute_templates(item, instance) for item in template_data]
        else:
            return template_data
            
    async def _fetch_pr_diff(self, diff_url: str) -> str:
        """Fetch PR diff content"""
        # This would make an HTTP request to fetch the diff
        # Placeholder implementation
        return "# Diff content would be fetched here"
        
    async def _extract_code_from_trigger(self, trigger_data: Dict, config: Dict) -> str:
        """Extract code from trigger data based on configuration"""
        if "pull_request" in trigger_data:
            # For PR events, return the diff or files changed
            return await self._fetch_pr_diff(trigger_data["pull_request"].get("diff_url", ""))
        elif "repository" in config:
            # Fetch specific files from repository
            return "# Repository code would be fetched here"
        else:
            return config.get("code", "No code provided")
            
    async def _notify_workflow_completion(self, instance: WorkflowInstance):
        """Send workflow completion notification"""
        workflow = self.workflows.get(instance.workflow_id)
        if not workflow:
            return
            
        # Determine notification channels from workflow config
        notification_config = workflow.__dict__.get("notification_config", {})
        if not notification_config:
            return
            
        # Prepare completion message
        status_emoji = "✅" if instance.status == "completed" else "❌"
        duration = ""
        if instance.end_time and instance.start_time:
            duration = f" in {(instance.end_time - instance.start_time).total_seconds():.1f}s"
            
        message = f"{status_emoji} Workflow '{workflow.name}' {instance.status}{duration}"
        
        if instance.error_message:
            message += f"\nError: {instance.error_message}"
            
        # Send to configured channels
        for channel_config in notification_config.get("channels", []):
            try:
                integration = await self.integrations.get_integration(channel_config["type"])
                if integration and hasattr(integration, 'send_message'):
                    await integration.send_message(
                        channel=channel_config.get("channel", "#general"),
                        message=message
                    )
            except Exception as e:
                logging.error(f"Failed to send workflow completion notification: {e}")

    async def run_scheduler(self):
        """Run scheduled workflow execution loop"""
        while True:
            try:
                current_time = datetime.now()
                
                # Check scheduled workflows
                for schedule_id, schedule_info in list(self.scheduled_workflows.items()):
                    if current_time >= schedule_info["next_run"]:
                        # Trigger workflow
                        workflow_id = schedule_info["workflow_id"]
                        await self.trigger_workflow(workflow_id, {
                            "scheduled": True,
                            "schedule_time": current_time.isoformat()
                        })
                        
                        # Update next run time
                        schedule_info["next_run"] = schedule_info["cron"].get_next(datetime)
                        
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logging.error(f"Error in workflow scheduler: {e}")
                await asyncio.sleep(60)
```

---

## 4) Integration Hub and Marketplace

**`/platform/integrations/hub.py`**
```python
from typing import Dict, Any, List, Optional, Type
from abc import ABC, abstractmethod
import aiohttp
import json
import logging
from datetime import datetime
import base64

class Integration(ABC):
    """Base class for all integrations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.lower().replace('integration', '')
        self._authenticated = False
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the external service"""
        pass
        
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection and return status"""
        pass
        
    @abstractmethod
    async def get_capabilities(self) -> List[str]:
        """Return list of available capabilities"""
        pass
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return await self.test_connection()

class SlackIntegration(Integration):
    """Slack integration for notifications and bot interactions"""
    
    async def authenticate(self) -> bool:
        """Authenticate using Bot User OAuth Token"""
        token = self.config.get("bot_token")
        if not token:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {token}"}
                async with session.post(
                    "https://slack.com/api/auth.test",
                    headers=headers
                ) as response:
                    data = await response.json()
                    self._authenticated = data.get("ok", False)
                    return self._authenticated
        except Exception as e:
            logging.error(f"Slack authentication failed: {e}")
            return False
            
    async def test_connection(self) -> Dict[str, Any]:
        """Test Slack connection"""
        try:
            if not self._authenticated:
                auth_result = await self.authenticate()
            else:
                auth_result = True
                
            return {
                "status": "connected" if auth_result else "failed",
                "service": "slack",
                "timestamp": datetime.utcnow().isoformat(),
                "authenticated": self._authenticated
            }
        except Exception as e:
            return {
                "status": "error",
                "service": "slack", 
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def get_capabilities(self) -> List[str]:
        """Return Slack integration capabilities"""
        return [
            "send_message",
            "send_file",
            "create_channel", 
            "invite_users",
            "set_status",
            "schedule_message",
            "create_reminder",
            "create_workflow_notification"
        ]
        
    async def send_message(self, channel: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send message to Slack channel"""
        if not self._authenticated:
            await self.authenticate()
            
        token = self.config.get("bot_token")
        
        payload = {
            "channel": channel,
            "text": message,
            **kwargs
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {token}"}
                async with session.post(
                    "https://slack.com/api/chat.postMessage",
                    headers=headers,
                    json=payload
                ) as response:
                    return await response.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}
            
    async def create_workflow_notification(self, workflow_result: Dict) -> Dict[str, Any]:
        """Create rich workflow notification"""
        workflow_name = workflow_result.get("workflow_name", "Unknown Workflow")
        status = workflow_result.get("status", "unknown")
        
        # Create rich message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🤖 Workflow: {workflow_name}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{status.title()}"
                    },
                    {
                        "type": "mrkdwn", 
                        "text": f"*Duration:*\n{workflow_result.get('duration', 'Unknown')}"
                    }
                ]
            }
        ]
        
        # Add action results if available
        if workflow_result.get("action_results"):
            action_summary = []
            for action, result in workflow_result["action_results"].items():
                emoji = "✅" if result.get('success') else "❌"
                action_summary.append(f"{emoji} {action}")
                
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Actions:*\n" + "\n".join(action_summary)
                }
            })
            
        # Add error details if workflow failed
        if status == "failed" and workflow_result.get("error_message"):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error:*\n```{workflow_result['error_message']}```"
                }
            })
            
        return await self.send_message(
            channel=self.config.get("default_channel", "#codessa"),
            text=f"Workflow {workflow_name} {status}",
            blocks=blocks
        )

class GitHubIntegration(Integration):
    """GitHub integration for repository management"""
    
    async def authenticate(self) -> bool:
        """Authenticate using Personal Access Token"""
        token = self.config.get("token")
        if not token:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"token {token}"}
                async with session.get(
                    "https://api.github.com/user",
                    headers=headers
                ) as response:
                    self._authenticated = response.status == 200
                    return self._authenticated
        except Exception as e:
            logging.error(f"GitHub authentication failed: {e}")
            return False
            
    async def test_connection(self) -> Dict[str, Any]:
        """Test GitHub connection"""
        try:
            if not self._authenticated:
                auth_result = await self.authenticate()
            else:
                auth_result = True
                
            return {
                "status": "connected" if auth_result else "failed",
                "service": "github",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "service": "github",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def get_capabilities(self) -> List[str]:
        """Return GitHub integration capabilities"""
        return [
            "create_pr_comment",
            "create_issue", 
            "register_webhook",
            "get_file_content",
            "commit_files",
            "create_release",
            "get_pr_diff",
            "create_pr_review"
        ]
        
    async def create_pr_comment(self, repository: str, pr_number: int, comment: str) -> Dict[str, Any]:
        """Add comment to pull request"""
        if not self._authenticated:
            await self.authenticate()
            
        token = self.config.get("token")
        
        payload = {"body": comment}
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github+json"
                }
                async with session.post(
                    f"https://api.github.com/repos/{repository}/issues/{pr_number}/comments",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 201:
                        return {"success": True, "comment": await response.json()}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def register_webhook(self, workflow_id: str, event_type: str, repository: str, config: Dict = None) -> Dict[str, Any]:
        """Register webhook for workflow triggers"""
        if not self._authenticated:
            await self.authenticate()
            
        token = self.config.get("token")
        webhook_url = self.config.get("webhook_base_url", "https://platform.codessa.dev")
        
        payload = {
            "name": "web",
            "active": True,
            "events": [event_type],
            "config": {
                "url": f"{webhook_url}/webhooks/github/{workflow_id}",
                "content_type": "json",
                "secret": self.config.get("webhook_secret", ""),
                "insecure_ssl": "0"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github+json"
                }
                async with session.post(
                    f"https://api.github.com/repos/{repository}/hooks",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 201:
                        return {"success": True, "webhook": await response.json()}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def create_pr_review(self, repository: str, pr_number: int, review_data: Dict) -> Dict[str, Any]:
        """Create a pull request review with AI analysis"""
        if not self._authenticated:
            await self.authenticate()
            
        token = self.config.get("token")
        
        # Format review data for GitHub API
        body = review_data.get("summary", "AI Code Review")
        event = "COMMENT"  # Could be REQUEST_CHANGES or APPROVE based on analysis
        
        # Add line-by-line comments if available
        comments = []
        for issue in review_data.get("issues", []):
            if issue.get("line"):
                comments.append({
                    "path": issue.get("file", "unknown"),
                    "line": issue["line"], 
                    "body": f"**{issue.get('type', 'Issue').title()}**: {issue.get('message', 'No description')}"
                })
                
        payload = {
            "body": body,
            "event": event,
            "comments": comments[:20]  # Limit comments to avoid API limits
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github+json"
                }
                async with session.post(
                    f"https://api.github.com/repos/{repository}/pulls/{pr_number}/reviews",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        return {"success": True, "review": await response.json()}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

class NotionIntegration(Integration):
    """Notion integration for documentation and knowledge management"""
    
    async def authenticate(self) -> bool:
        """Authenticate using Integration Token"""
        token = self.config.get("integration_token")
        if not token:
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28"
                }
                async with session.get(
                    "https://api.notion.com/v1/users/me",
                    headers=headers
                ) as response:
                    self._authenticated = response.status == 200
                    return self._authenticated
        except Exception as e:
            logging.error(f"Notion authentication failed: {e}")
            return False
            
    async def test_connection(self) -> Dict[str, Any]:
        """Test Notion connection"""
        try:
            if not self._authenticated:
                auth_result = await self.authenticate()
            else:
                auth_result = True
                
            return {
                "status": "connected" if auth_result else "failed",
                "service": "notion",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "service": "notion",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def get_capabilities(self) -> List[str]:
        """Return Notion integration capabilities"""
        return [
            "create_page",
            "update_page",
            "create_database_entry",
            "search_pages",
            "create_documentation",
            "update_documentation"
        ]
        
    async def create_documentation_page(self, title: str, content: str, parent_id: str) -> Dict[str, Any]:
        """Create a new documentation page"""
        if not self._authenticated:
            await self.authenticate()
            
        token = self.config.get("integration_token")
        
        # Convert markdown content to Notion blocks
        blocks = await self._markdown_to_blocks(content)
        
        payload = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {"content": title}
                        }
                    ]
                }
            },
            "children": blocks
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                }
                async with session.post(
                    "https://api.notion.com/v1/pages",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        return {"success": True, "page": await response.json()}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _markdown_to_blocks(self, markdown_content: str) -> List[Dict]:
        """Convert markdown to Notion blocks"""
        blocks = []
        lines = markdown_content.split('\n')
        
        current_code_block = []
        in_code_block = False
        code_language = ""
        
        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # End of code block
                    if current_code_block:
                        blocks.append({
                            "object": "block",
                            "type": "code",
                            "code": {
                                "language": code_language or "plain text",
                                "rich_text": [{"type": "text", "text": {"content": '\n'.join(current_code_block)}}]
                            }
                        })
                    current_code_block = []
                    in_code_block = False
                    code_language = ""
                else:
                    # Start of code block
                    in_code_block = True
                    code_language = line[3:].strip() or "plain text"
            elif in_code_block:
                current_code_block.append(line)
            elif line.startswith('# '):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('## '):
                blocks.append({
                    "object": "block",
                    "type": "heading_2", 
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    }
                })
            elif line.startswith('### '):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    }
                })
            elif line.strip():
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    }
                })
                
        return blocks

class JiraIntegration(Integration):
    """Jira integration for issue tracking and project management"""
    
    async def authenticate(self) -> bool:
        """Authenticate using API token"""
        base_url = self.config.get("base_url")
        email = self.config.get("email")
        api_token = self.config.get("api_token")
        
        if not all([base_url, email, api_token]):
            return False
            
        try:
            auth_string = base64.b64encode(f"{email}:{api_token}".encode()).decode()
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Basic {auth_string}"}
                async with session.get(
                    f"{base_url}/rest/api/3/myself",
                    headers=headers
                ) as response:
                    self._authenticated = response.status == 200
                    return self._authenticated
        except Exception as e:
            logging.error(f"Jira authentication failed: {e}")
            return False
            
    async def test_connection(self) -> Dict[str, Any]:
        """Test Jira connection"""
        try:
            if not self._authenticated:
                auth_result = await self.authenticate()
            else:
                auth_result = True
                
            return {
                "status": "connected" if auth_result else "failed",
                "service": "jira",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "service": "jira",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def get_capabilities(self) -> List[str]:
        """Return Jira integration capabilities"""
        return [
            "create_issue",
            "update_issue",
            "add_comment",
            "search_issues",
            "create_epic",
            "link_issues",
            "transition_issue",
            "create_security_issues"
        ]
        
    async def create_security_issues(self, security_results: Dict) -> Dict[str, Any]:
        """Create Jira issues from security scan results"""
        if not self._authenticated:
            await self.authenticate()
            
        base_url = self.config.get("base_url")
        email = self.config.get("email")
        api_token = self.config.get("api_token")
        project_key = self.config.get("project_key", "SEC")
        
        auth_string = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        
        issues_created = []
        vulnerabilities = security_results.get("security_analysis", {}).get("llm_analysis", {}).get("vulnerabilities", [])
        
        for vulnerability in vulnerabilities:
            # Only create issues for high/critical vulnerabilities
            if vulnerability.get("severity") in ["High", "Critical"]:
                
                issue_payload = {
                    "fields": {
                        "project": {"key": project_key},
                        "summary": f"Security: {vulnerability.get('title', 'Unknown Vulnerability')}",
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": f"Severity: {vulnerability.get('severity', 'Unknown')}\n\n"}
                                    ]
                                },
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": f"Description: {vulnerability.get('description', 'No description')}"}
                                    ]
                                },
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": f"Remediation: {vulnerability.get('remediation', 'No remediation provided')}"}
                                    ]
                                }
                            ]
                        },
                        "issuetype": {"name": "Bug"},
                        "priority": {"name": "High" if vulnerability.get("severity") == "High" else "Highest"},
                        "labels": ["security", "automated", vulnerability.get("type", "unknown").replace(" ", "-")]
                    }
                }
                
                try:
                    async with aiohttp.ClientSession() as session:
                        headers = {
                            "Authorization": f"Basic {auth_string}",
                            "Content-Type": "application/json"
                        }
                        async with session.post(
                            f"{base_url}/rest/api/3/issue",
                            headers=headers,
                            json=issue_payload
                        ) as response:
                            if response.status == 201:
                                result = await response.json()
                                issues_created.append({
                                    "key": result["key"],
                                    "vulnerability": vulnerability["title"],
                                    "severity": vulnerability["severity"],
                                    "url": f"{base_url}/browse/{result['key']}"
                                })
                except Exception as e:
                    logging.error(f"Failed to create Jira issue for vulnerability: {e}")
                    
        return {
            "success": True,
            "issues_created": len(issues_created),
            "issues": issues_created
        }

class IntegrationHub:
    """Central hub for managing all integrations"""
    
    def __init__(self):
        self.integrations: Dict[str, Integration] = {}
        self.available_integrations: Dict[str, Type[Integration]] = {
            "slack": SlackIntegration,
            "github": GitHubIntegration,
            "notion": NotionIntegration,
            "jira": JiraIntegration,
            # Additional integrations can be added here
            "discord": DiscordIntegration,  # Would implement similarly
            "teams": TeamsIntegration,      # Would implement similarly
            "confluence": ConfluenceIntegration,  # Would implement similarly
        }
        
    async def register_integration(self, integration_type: str, config: Dict[str, Any]) -> bool:
        """Register and authenticate an integration"""
        if integration_type not in self.available_integrations:
            raise ValueError(f"Unknown integration type: {integration_type}")
            
        integration_class = self.available_integrations[integration_type]
        integration = integration_class(config)
        
        # Test authentication
        if await integration.authenticate():
            self.integrations[integration_type] = integration
            logging.info(f"Successfully registered {integration_type} integration")
            return True
        else:
            raise Exception(f"Failed to authenticate {integration_type} integration")
            
    async def get_integration(self, integration_type: str) -> Optional[Integration]:
        """Get registered integration"""
        return self.integrations.get(integration_type)
        
    async def execute_integration_action(self, integration_type: str, action: str, **kwargs) -> Dict[str, Any]:
        """Execute action on specific integration"""
        integration = self.integrations.get(integration_type)
        if not integration:
            raise ValueError(f"Integration {integration_type} not registered")
            
        # Get the method dynamically
        method = getattr(integration, action, None)
        if not method:
            raise ValueError(f"Action {action} not available for {integration_type}")
            
        return await method(**kwargs)
        
    async def broadcast_notification(self, message: str, channels: List[str] = None) -> Dict[str, Any]:
        """Send notification to multiple integrations"""
        results = {}
        
        # Default channels if none specified
        if not channels:
            channels = ["slack", "teams", "discord"]
            
        for channel in channels:
            integration = self.integrations.get(channel)
            if integration and hasattr(integration, 'send_message'):
                try:
                    result = await integration.send_message(
                        channel=integration.config.get("default_channel", "#general"),
                        message=message
                    )
                    results[channel] = {"status": "success", "result": result}
                except Exception as e:
                    results[channel] = {"status": "error", "error": str(e)}
                    
        return results
        
    async def health_check_all(self) -> Dict[str, Any]:
        """Perform health check on all registered integrations"""
        results = {}
        
        for integration_type, integration in self.integrations.items():
            try:
                health_result = await integration.health_check()
                results[integration_type] = health_result
            except Exception as e:
                results[integration_type] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        return results

# Placeholder classes for additional integrations
class DiscordIntegration(Integration):
    """Discord integration - would implement similarly to Slack"""
    async def authenticate(self) -> bool:
        return True
    async def test_connection(self) -> Dict[str, Any]:
        return {"status": "not_implemented", "service": "discord"}
    async def get_capabilities(self) -> List[str]:
        return ["send_message"]

class TeamsIntegration(Integration):
    """Microsoft Teams integration - would implement similarly to Slack"""
    async def authenticate(self) -> bool:
        return True
    async def test_connection(self) -> Dict[str, Any]:
        return {"status": "not_implemented", "service": "teams"}
    async def get_capabilities(self) -> List[str]:
        return ["send_message"]

class ConfluenceIntegration(Integration):
    """Confluence integration - would implement similarly to Notion"""
    async def authenticate(self) -> bool:
        return True
    async def test_connection(self) -> Dict[str, Any]:
        return {"status": "not_implemented", "service": "confluence"}
    async def get_capabilities(self) -> List[str]:
        return ["create_page", "update_page"]
```

---

## 5) Workflow Templates and Examples

**`/platform/templates/workflow_templates.py`**
```python
from typing import Dict, List
from ..workflows.engine import Workflow, WorkflowTrigger, WorkflowAction, TriggerType, ActionType

class WorkflowTemplates:
    """Collection of pre-built workflow templates for common development scenarios"""
    
    @staticmethod
    def automated_pr_review() -> Workflow:
        """Comprehensive automated PR review workflow"""
        return Workflow(
            name="Automated PR Review",
            description="Automatically review pull requests with AI agents and post results",
            triggers=[
                WorkflowTrigger(
                    trigger_type=TriggerType.GIT_PR,
                    config={
                        "repository": "{{org}}/{{repo}}",  # Template variables
                        "actions": ["opened", "synchronize", "ready_for_review"]
                    },
                    conditions={
                        "pull_request.draft": False  # Only review non-draft PRs
                    }
                )
            ],
            actions=[
                WorkflowAction(
                    action_id="code_review",
                    action_type=ActionType.AI_AGENT_TASK,
                    config={
                        "capability": "code_review",
                        "input": {
                            "code": "{{trigger.pull_request.diff}}",
                            "language": "{{trigger.pull_request.language}}",
                            "context": "{{trigger.pull_request.title}}: {{trigger.pull_request.body}}"
                        },
                        "priority": 2
                    },
                    timeout_minutes=10
                ),
                WorkflowAction(
                    action_id="security_scan",
                    action_type=ActionType.AI_AGENT_TASK,
                    config={
                        "capability": "security_analysis",
                        "input": {
                            "code": "{{trigger.pull_request.diff}}",
                            "language": "{{trigger.pull_request.language}}",
                            "include_dependencies": True
                        },
                        "priority": 1  # High priority for security
                    },
                    timeout_minutes=15
                ),
                WorkflowAction(
                    action_id="post_review",
                    action_type=ActionType.INTEGRATION_ACTION,
                    config={
                        "integration": "github",
                        "action": "create_pr_review",
                        "parameters": {
                            "repository": "{{trigger.repository.full_name}}",
                            "pr_number": "{{trigger.pull_request.number}}",
                            "review_data": "{{action_results.code_review.agent_result}}"
                        }
                    },
                    depends_on=["code_review"],
                    timeout_minutes=5
                ),
                WorkflowAction(
                    action_id="create_security_issues",
                    action_type=ActionType.INTEGRATION_ACTION,
                    config={
                        "integration": "jira",
                        "action": "create_security_issues",
                        "parameters": {
                            "security_results": "{{action_results.security_scan.agent_result}}"
                        }
                    },
                    depends_on=["security_scan"],
                    condition="action_results.security_scan.agent_result.security_analysis.overall_risk_score > 5.0",
                    timeout_minutes=10
                ),
                WorkflowAction(
                    action_id="notify_team",
                    action_type=ActionType.NOTIFY,
                    config={
                        "integration": "slack",
                        "channel": "#dev-reviews",
                        "message": "🔍 AI Review completed for PR #{{trigger.pull_request.number}}: {{trigger.pull_request.title}}\n" +
                                  "Review: {{action_results.post_review.success}}\n" +
                                  "Security Issues: {{action_results.create_security_issues.issues_created}} created"
                    },
                    depends_on=["post_review", "create_security_issues"],
                    timeout_minutes=2
                )
            ],
            tags=["pr", "code-review", "security", "automated"]
        )
        
    @staticmethod
    def daily_security_scan() -> Workflow:
        """Daily security scanning across repositories"""
        return Workflow(
            name="Daily Security Scan",
            description="Scan all repositories for security vulnerabilities daily",
            triggers=[
                WorkflowTrigger(
                    trigger_type=TriggerType.SCHEDULE,
                    config={
                        "cron": "0 9 * * 1-5",  # Weekdays at 9 AM
                        "timezone": "UTC"
                    }
                )
            ],
            actions=[
                WorkflowAction(
                    action_id="scan_repositories",
                    action_type=ActionType.AI_AGENT_TASK,
                    config={
                        "capability": "security_analysis",
                        "input": {
                            "repositories": ["{{env.PRIMARY_REPO}}", "{{env.SECONDARY_REPO}}"],
                            "scan_type": "comprehensive",
                            "include_dependencies": True
                        },
                        "priority": 3
                    },
                    timeout_minutes=45
                ),
                WorkflowAction(
                    action_id="create_security_report",
                    action_type=ActionType.INTEGRATION_ACTION,
                    config={
                        "integration": "notion",
                        "action": "create_documentation_page",
                        "parameters": {
                            "title": "Security Scan Report - {{date}}",
                            "content": "{{action_results.scan_repositories.agent_result.security_analysis}}",
                            "parent_id": "{{env.NOTION_SECURITY_PAGE_ID}}"
                        }
                    },
                    depends_on=["scan_repositories"],
                    timeout_minutes=10
                ),
                WorkflowAction(
                    action_id="create_critical_issues",
                    action_type=ActionType.INTEGRATION_ACTION,
                    config={
                        "integration": "jira",
                        "action": "create_security_issues",
                        "parameters": {
                            "security_results": "{{action_results.scan_repositories.agent_result}}"
                        }
                    },
                    depends_on=["scan_repositories"],
                    condition="action_results.scan_repositories.agent_result.security_analysis.overall_risk_score > 7.0",
                    timeout_minutes=15
                ),
                WorkflowAction(
                    action_id="notify_security_team",
                    action_type=ActionType.NOTIFY,
                    config={
                        "integration": "slack",
                        "channel": "#security",
                        "message": "🛡️ Daily Security Scan Complete\n" +
                                  "Report: {{action_results.create_security_report.integration_result.page.url}}\n" +
                                  "Critical Issues Created: {{action_results.create_critical_issues.issues_created}}"
                    },
                    depends_on=["create_security_report", "create_critical_issues"],
                    timeout_minutes=2
                )
            ],
            tags=["security", "scheduled", "reporting"]
        )
        
    @staticmethod
    def documentation_update_pipeline() -> Workflow:
        """Update documentation when code changes"""
        return Workflow(
            name="Documentation Update Pipeline",
            description="Update documentation automatically when code changes are detected",
            triggers=[
                WorkflowTrigger(
                    trigger_type=TriggerType.GIT_PUSH,
                    config={
                        "repository": "{{org}}/{{repo}}",
                        "branches": ["main", "master"],
                        "paths": ["src/**", "lib/**", "api/**"]  # Only trigger on source changes
                    }
                )
            ],
            actions=[
                WorkflowAction(
                    action_id="analyze_changes",
                    action_type=ActionType.AI_AGENT_TASK,
                    config={
                        "capability": "documentation",
                        "input": {
                            "code_changes": "{{trigger.commits}}",
                            "repository": "{{trigger.repository.full_name}}",
                            "doc_types": ["api", "readme", "changelog"]
                        },
                        "priority": 3
                    },
                    timeout_minutes=20
                ),
                WorkflowAction(
                    action_id="update_notion_docs",
                    action_type=ActionType.INTEGRATION_ACTION,
                    config={
                        "integration": "notion",
                        "action": "update_documentation",
                        "parameters": {
                            "updates": "{{action_results.analyze_changes.agent_result.documentation_updates}}",
                            "base_page_id": "{{env.NOTION_DOCS_PAGE_ID}}"
                        }
                    },
                    depends_on=["analyze_changes"],
                    condition="action_results.analyze_changes.agent_result.requires_update == true",
                    timeout_minutes=10
                ),
                WorkflowAction(
                    action_id="create_pr_for_readme",
                    action_type=ActionType.INTEGRATION_ACTION,
                    config={
                        "integration": "github",
                        "action": "create_pr",
                        "parameters": {
                            "repository": "{{trigger.repository.full_name}}",
                            "title": "📚 Update README and documentation",
                            "body": "Automated documentation update based on recent code changes.\n\nChanges:\n{{action_results.analyze_changes.agent_result.summary}}",
                            "files": "{{action_results.analyze_changes.agent_result.updated_files}}",
                            "base": "main"
                        }
                    },
                    depends_on=["analyze_changes"],
                    condition="action_results.analyze_changes.agent_result.readme_changes != null",
                    timeout_minutes=15
                ),
                WorkflowAction(
                    action_id="notify_docs_update",
                    action_type=ActionType.NOTIFY,
                    config={
                        "integration": "slack",
                        "channel": "#documentation",
                        "message": "📚 Documentation updated for {{trigger.repository.name}}\n" +
                                  "Notion: {{action_results.update_notion_docs.success}}\n" +
                                  "PR Created: {{action_results.create_pr_for_readme.success}}"
                    },
                    depends_on=["update_notion_docs", "create_pr_for_readme"],
                    timeout_minutes=2
                )
            ],
            tags=["documentation", "automation", "git-push"]
        )
        
    @staticmethod
    def incident_response_workflow() -> Workflow:
        """Automated incident response workflow"""
        return Workflow(
            name="Incident Response",
            description="Automated response to production incidents and alerts",
            triggers=[
                WorkflowTrigger(
                    trigger_type=TriggerType.WEBHOOK,
                    config={
                        "webhook_path": "/incidents/alert",
                        "required_fields": ["severity", "service", "description"]
                    }
                ),
                WorkflowTrigger(
                    trigger_type=TriggerType.INTEGRATION_EVENT,
                    config={
                        "integration": "datadog",  # Example monitoring integration
                        "event_types": ["alert.triggered"]
                    }
                )
            ],
            actions=[
                WorkflowAction(
                    action_id="analyze_incident",
                    action_type=ActionType.AI_AGENT_TASK,
                    config={
                        "capability": "debugging",
                        "input": {
                            "error_details": "{{trigger.description}}",
                            "service": "{{trigger.service}}",
                            "severity": "{{trigger.severity}}",
                            "logs": "{{trigger.logs}}"
                        },
                        "priority": 1  # Highest priority
                    },
                    timeout_minutes=5
                ),
                WorkflowAction(
                    action_id="create_incident_ticket",
                    action_type=ActionType.INTEGRATION_ACTION,
                    config={
                        "integration": "jira",
                        "action": "create_issue",
                        "parameters": {
                            "project_key": "INC",
                            "issue_type": "Incident",
                            "priority": "{{trigger.severity}}",
                            "summary": "INCIDENT: {{trigger.service}} - {{trigger.description}}",
                            "description": "Automated incident created\n\nAnalysis: {{action_results.analyze_incident.agent_result.analysis}}\n\nRecommended Actions: {{action_results.analyze_incident.agent_result.recommendations}}"
                        }
                    },
                    depends_on=["analyze_incident"],
                    timeout_minutes=3
                ),
                WorkflowAction(
                    action_id="notify_oncall",
                    action_type=ActionType.NOTIFY,
                    config={
                        "integration": "slack",
                        "channel": "#incidents",
                        "message": "🚨 INCIDENT ALERT 🚨\n" +
                                  "Service: {{trigger.service}}\n" +
                                  "Severity: {{trigger.severity}}\n" +
                                  "Description: {{trigger.description}}\n\n" +
                                  "AI Analysis: {{action_results.analyze_incident.agent_result.summary}}\n" +
                                  "Ticket: {{action_results.create_incident_ticket.integration_result.key}}"
                    },
                    depends_on=["create_incident_ticket"],
                    timeout_minutes=1
                ),
                WorkflowAction(
                    action_id="suggest_hotfix",
                    action_type=ActionType.AI_AGENT_TASK,
                    config={
                        "capability": "code_generation",
                        "input": {
                            "issue_description": "{{trigger.description}}",
                            "error_analysis": "{{action_results.analyze_incident.agent_result}}",
                            "service_context": "{{trigger.service}}"
                        },
                        "priority": 1
                    },
                    depends_on=["analyze_incident"],
                    condition="trigger.severity in ['critical', 'high']",
                    timeout_minutes=10
                ),
                WorkflowAction(
                    action_id="create_hotfix_pr",
                    action_type=ActionType.INTEGRATION_ACTION,
                    config={
                        "integration": "github", 
                        "action": "create_pr",
                        "parameters": {
                            "repository": "{{trigger.service_repository}}",
                            "title": "🚨 HOTFIX: {{trigger.service}} incident response",
                            "body": "Emergency hotfix for incident {{action_results.create_incident_ticket.integration_result.key}}\n\n{{action_results.suggest_hotfix.agent_result.explanation}}",
                            "files": "{{action_results.suggest_hotfix.agent_result.files}}",
                            "base": "main",
                            "draft": False
                        }
                    },
                    depends_on=["suggest_hotfix", "create_incident_ticket"],
                    condition="action_results.suggest_hotfix.agent_result.confidence > 0.8",
                    timeout_minutes=5
                )
            ],
            tags=["incident", "emergency", "automated-response"]
        )

# Usage example for registering templates
async def setup_default_workflows(workflow_engine, organization_config):
    """Set up default workflows for an organization"""
    templates = WorkflowTemplates()
    
    # Customize templates with organization-specific config
    pr_review = templates.automated_pr_review()
    # Replace template variables
    for trigger in pr_review.triggers:
        if "{{org}}" in str(trigger.config):
            trigger.config = json.loads(
                json.dumps(trigger.config).replace("{{org}}", organization_config["github_org"])
            )
    
    security_scan = templates.daily_security_scan()
    docs_pipeline = templates.documentation_update_pipeline()
    incident_response = templates.incident_response_workflow()
    
    # Register workflows
    workflows = [pr_review, security_scan, docs_pipeline, incident_response]
    registered_ids = []
    
    for workflow in workflows:
        workflow_id = await workflow_engine.register_workflow(workflow)
        registered_ids.append(workflow_id)
        
    return registered_ids
```

---

## 6) Platform API and SDK

**`/platform/api/main.py`**
```python
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors