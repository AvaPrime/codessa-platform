from datetime import timedelta, datetime
from typing import Dict, Any, List
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from dataclasses import dataclass
import asyncio
import json
import nats
import psycopg
import os
import time
import uuid

from orchestrator.workflows.router import route_task
from config.schemas.task_message import TaskMessage, TaskPayload
from config.schemas.result_message import ResultMessage
from config.schemas.message_handler import ProductionMessageHandler


@dataclass
class TaskRequest:
    task_id: str
    role: str
    payload: Dict[str, Any]
    priority: int = 1
    timeout_seconds: int = 300
    retry_attempts: int = 3
    user_id: str = None
    idempotency_key: str = None

@dataclass
class TaskResult:
    task_id: str
    status: str
    result: Dict[str, Any]
    role: str = None
    error: str = None
    duration_seconds: float = 0

# Workflow Definitions
@workflow.defn
class TaskOrchestrationWorkflow:
    """Main workflow for orchestrating agent tasks with retries and saga patterns"""
    
    @workflow.run
    async def run(self, task_request: TaskRequest) -> TaskResult:
        """Execute a task with full orchestration"""
        
        # Set workflow timeout
        workflow.set_timeout(timedelta(seconds=task_request.timeout_seconds + 60))
        
        try:
            # Step 1: Validate and prepare task
            validated_task = await workflow.execute_activity(
                validate_task_activity,
                task_request,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=2)
            )
            
            # Step 2: Route to appropriate agent
            routing_info = await workflow.execute_activity(
                route_task_activity,
                validated_task,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )
            
            # Step 3: Execute task with agent
            task_result = await workflow.execute_activity(
                execute_agent_task_activity,
                validated_task,
                routing_info,
                start_to_close_timeout=timedelta(seconds=task_request.timeout_seconds),
                retry_policy=RetryPolicy(
                    maximum_attempts=task_request.retry_attempts,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=60),
                    backoff_coefficient=2.0
                )
            )
            
            # Step 4: Persist results
            await workflow.execute_activity(
                persist_result_activity,
                task_result,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5)
            )
            
            # Step 5: Send notifications if needed
            if task_result.status == "completed":
                await workflow.execute_activity(
                    notify_completion_activity,
                    task_result,
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )
            
            return task_result
            
        except Exception as e:
            # Compensation/rollback logic
            workflow.logger.error(f"Task orchestration failed for task {task_request.task_id}: {e}")
            await workflow.execute_activity(
                handle_task_failure_activity,
                task_request,
                str(e),
                start_to_close_timeout=timedelta(seconds=30)
            )
            
            return TaskResult(
                task_id=task_request.task_id,
                role=task_request.role,
                status="failed",
                result={},
                error=str(e)
            )

@workflow.defn
class MultiAgentSagaWorkflow:
    """Saga pattern for coordinating multiple agents"""
    
    @workflow.run
    async def run(self, saga_request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multi-agent saga with compensation"""
        
        completed_steps = []
        
        try:
            for step in saga_request["steps"]:
                result = await workflow.execute_activity(
                    execute_saga_step_activity,
                    step,
                    start_to_close_timeout=timedelta(seconds=step.get("timeout", 300)),
                    retry_policy=RetryPolicy(maximum_attempts=3)
                )
                completed_steps.append({"step": step, "result": result})
            
            return {"status": "completed", "results": completed_steps}
            
        except Exception as e:
            # Compensate completed steps in reverse order
            for step_info in reversed(completed_steps):
                try:
                    await workflow.execute_activity(
                        compensate_saga_step_activity,
                        step_info["step"],
                        step_info["result"],
                        start_to_close_timeout=timedelta(seconds=60)
                    )
                except Exception as comp_error:
                    workflow.logger.error(f"Compensation failed: {comp_error}")
            
            return {"status": "failed", "error": str(e), "compensated_steps": len(completed_steps)}

# Activity Definitions
@activity.defn
async def validate_task_activity(task_request: TaskRequest) -> TaskRequest:
    """Validate task request and add idempotency key"""
    activity.logger.info(f"Validating task {task_request.task_id}")
    # Add idempotency handling
    if task_request.idempotency_key is None:
        task_request.idempotency_key = f"{task_request.task_id}_{hash(json.dumps(task_request.payload, sort_keys=True))}"
    
    # Validate required fields
    if not task_request.role or not task_request.payload:
        raise ValueError("Invalid task request: missing role or payload")
    
    activity.logger.info(f"Task {task_request.task_id} validated successfully.")
    return task_request

@activity.defn
async def route_task_activity(task_request: TaskRequest) -> Dict[str, Any]:
    """Route task to appropriate agent with load balancing"""
    activity.logger.info(f"Routing task {task_request.task_id} for role {task_request.role}")
    
    routing_info = route_task({
        "role": task_request.role,
        "priority": task_request.priority,
        "budget": task_request.payload.get("budget", "standard")
    })
    
    activity.logger.info(f"Task {task_request.task_id} routed to: {routing_info}")
    return routing_info

@activity.defn
async def execute_agent_task_activity(task_request: TaskRequest, routing_info: Dict[str, Any]) -> TaskResult:
    """Execute task with the assigned agent using ProductionMessageHandler"""
    start_time = time.time()
    activity.logger.info(f"Executing task {task_request.task_id} for role {task_request.role} via NATS.")
    
    message_handler = None
    nc = None
    try:
        # Initialize message handler
        message_handler = ProductionMessageHandler()
        await message_handler.initialize()
        nc = message_handler.nc
        
        # Create structured task message
        task_payload = TaskPayload(
            task_id=task_request.task_id,
            description=task_request.payload.get("description", ""),
            context=task_request.payload.get("context", {}),
            requirements=task_request.payload.get("requirements", []),
            tech_stack=task_request.payload.get("tech_stack", []),
            priority=task_request.priority,
            timeout_seconds=task_request.timeout_seconds
        )
        
        task_message = TaskMessage(
            task_id=task_request.task_id,
            agent_role=task_request.role,
            payload=task_payload,
            correlation_id=task_request.idempotency_key or str(uuid.uuid4())
        )
        
        # Publish task using message handler
        activity.logger.info(f"Publishing task {task_request.task_id} to role {task_request.role}")
        await message_handler.publish_message(
            message=task_message,
            headers={
                "task_id": task_request.task_id,
                "orchestrator_id": "temporal_workflow",
                "traceparent": f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"
            }
        )
        
        # Wait for result with timeout
        result_subject = f"results.{task_request.task_id}"
        
        # Subscribe to result
        js = nc.jetstream()
        sub = await js.subscribe(result_subject, durable=f"result_{task_request.task_id}")
        
        # Wait for result with timeout
        activity.logger.info(f"Waiting for result for task {task_request.task_id} on subject {result_subject}")
        try:
            msg = await asyncio.wait_for(sub.next_msg(), timeout=task_request.timeout_seconds)
            
            # Parse result message using message handler validation
            try:
                result_message = await message_handler._parse_and_validate_message(
                    msg, ResultMessage
                )
                await msg.ack()
                
                activity.logger.info(f"Received result for task {task_request.task_id}")
                
                return TaskResult(
                    task_id=task_request.task_id,
                    role=task_request.role,
                    status=result_message.payload.status,
                    result={"content": result_message.payload.result},
                    duration_seconds=time.time() - start_time
                )
            except Exception as parse_error:
                # Fallback to legacy parsing for compatibility
                activity.logger.warning(f"Failed to parse structured result, falling back to legacy format: {parse_error}")
                result_data = json.loads(msg.data.decode())
                await msg.ack()
                
                return TaskResult(
                    task_id=task_request.task_id,
                    role=task_request.role,
                    status=result_data.get("status", "completed"),
                    result=result_data.get("result", {}),
                    duration_seconds=time.time() - start_time
                )
            
        except asyncio.TimeoutError:
            activity.logger.error(f"Task {task_request.task_id} timed out after {task_request.timeout_seconds} seconds")
            raise Exception(f"Task {task_request.task_id} timed out after {task_request.timeout_seconds} seconds")
            
    except Exception as e:
        activity.logger.error(f"Error executing task {task_request.task_id}: {e}")
        raise  # Re-raise exception to let Temporal handle retries/failure
    
    finally:
        if message_handler:
            await message_handler.close()
        elif nc:
            await nc.close()

@activity.defn
async def persist_result_activity(task_result: TaskResult) -> bool:
    """Persist task result to database"""
    activity.logger.info(f"Persisting result for task {task_result.task_id}")
    
    try:
        async with await psycopg.AsyncConnection.connect(
            os.getenv("POSTGRES_URI", "postgresql://user:pass@db:5432/factory")
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO results (task_id, role, content, metadata, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (task_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                    """,
                    (
                        task_result.task_id,
                        task_result.role,
                        json.dumps(task_result.result),
                        json.dumps({
                            "duration_seconds": task_result.duration_seconds,
                            "error": task_result.error
                        }),
                        task_result.status
                    )
                )
                await conn.commit()
        activity.logger.info(f"Successfully persisted result for task {task_result.task_id}")
        return True
    except Exception as e:
        activity.logger.error(f"Failed to persist result for task {task_result.task_id}: {e}")
        raise Exception(f"Failed to persist result: {e}")

@activity.defn
async def notify_completion_activity(task_result: TaskResult) -> bool:
    """Send completion notifications"""
    # Implement notification logic (webhooks, emails, etc.)
    activity.logger.info(f"Notifying completion for task {task_result.task_id}")
    print(f"Task {task_result.task_id} completed successfully")
    return True

@activity.defn
async def handle_task_failure_activity(task_request: TaskRequest, error: str) -> bool:
    """Handle task failure with cleanup"""
    activity.logger.error(f"Handling failure for task {task_request.task_id}. Error: {error}")
    # Implement failure handling (DLQ, alerts, cleanup)
    print(f"Task {task_request.task_id} failed: {error}")
    return True

@activity.defn
async def execute_saga_step_activity(step: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single step in a saga"""
    # Implement saga step execution
    activity.logger.info(f"Executing saga step: {step.get('name', 'Unnamed')}")
    return {"status": "completed", "data": step}

@activity.defn
async def compensate_saga_step_activity(step: Dict[str, Any], result: Dict[str, Any]) -> bool:
    """Compensate a saga step"""
    # Implement compensation logic
    activity.logger.info(f"Compensating saga step: {step.get('name', 'Unnamed')}")
    return True