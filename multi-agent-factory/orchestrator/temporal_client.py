from temporalio.client import Client, TLSConfig
from temporalio.worker import Worker
from orchestrator.workflows.task_workflows import (
    TaskOrchestrationWorkflow,
    MultiAgentSagaWorkflow,
    validate_task_activity,
    route_task_activity,
    execute_agent_task_activity,
    persist_result_activity,
    notify_completion_activity,
    handle_task_failure_activity,
    execute_saga_step_activity,
    compensate_saga_step_activity
)
import os
import asyncio
from typing import Optional

class TemporalManager:
    """Manages Temporal client and worker lifecycle"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.host = os.getenv("TEMPORAL_HOST", "temporal")
        self.port = int(os.getenv("TEMPORAL_PORT", "7233"))
        self.namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
        
    async def connect(self) -> Client:
        """Connect to Temporal server"""
        if not self.client:
            self.client = await Client.connect(
                f"{self.host}:{self.port}",
                namespace=self.namespace
            )
        return self.client
    
    async def start_worker(self, task_queue: str = "maf-task-queue") -> Worker:
        """Start Temporal worker"""
        if not self.client:
            await self.connect()
            
        self.worker = Worker(
            self.client,
            task_queue=task_queue,
            workflows=[
                TaskOrchestrationWorkflow,
                MultiAgentSagaWorkflow
            ],
            activities=[
                validate_task_activity,
                route_task_activity,
                execute_agent_task_activity,
                persist_result_activity,
                notify_completion_activity,
                handle_task_failure_activity,
                execute_saga_step_activity,
                compensate_saga_step_activity
            ]
        )
        
        print(f"🔄 Starting Temporal worker on task queue: {task_queue}")
        await self.worker.run()
        
    async def execute_task_workflow(self, task_request) -> str:
        """Execute a task workflow"""
        if not self.client:
            await self.connect()
            
        workflow_id = f"task-{task_request.task_id}"
        
        handle = await self.client.start_workflow(
            TaskOrchestrationWorkflow.run,
            task_request,
            id=workflow_id,
            task_queue="maf-task-queue"
        )
        
        return handle.id
    
    async def execute_saga_workflow(self, saga_request: dict) -> str:
        """Execute a multi-agent saga workflow"""
        if not self.client:
            await self.connect()
            
        workflow_id = f"saga-{saga_request['saga_id']}"
        
        handle = await self.client.start_workflow(
            MultiAgentSagaWorkflow.run,
            saga_request,
            id=workflow_id,
            task_queue="maf-task-queue"
        )
        
        return handle.id
    
    async def get_workflow_result(self, workflow_id: str):
        """Get workflow execution result"""
        if not self.client:
            await self.connect()
            
        handle = self.client.get_workflow_handle(workflow_id)
        return await handle.result()
    
    async def close(self):
        """Close connections"""
        if self.worker:
            await self.worker.shutdown()
        if self.client:
            await self.client.close()

# Global instance
temporal_manager = TemporalManager()