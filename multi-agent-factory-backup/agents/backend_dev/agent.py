import os, asyncio, json
import nats
import redis.asyncio as redis
from datetime import datetime
import sys
sys.path.append('/app')
from memory.vector_store import search_by_text
from llm.openai_helpers import generate_markdown
from config.schemas.message_handler import ProductionMessageHandler
from config.schemas.task_message import TaskMessage
from config.schemas.result_message import ResultMessage, ResultPayload
from config.schemas.messages import MessageType
import logging

logger = logging.getLogger(__name__)

NATS_URL   = os.getenv("NATS_URL", "nats://nats:4222")
ROLE       = os.getenv("AGENT_ROLE", "backend_dev")
SUBJECT    = f"tasks.{ROLE}"
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

class BackendDevAgent:
    def __init__(self):
        self.agent_id = f"backend_dev_{os.getpid()}"
        self.message_handler = None
    
    async def initialize(self):
        """Initialize the production message handler."""
        nc = await nats.connect(NATS_URL)
        secret = os.getenv("TASK_SIGNING_SECRET", "default-secret")
        self.message_handler = ProductionMessageHandler(nc, secret, self.agent_id)
        
    async def handle_task_message(self, task: TaskMessage, headers: dict):
        """Handle incoming task messages with proper validation."""
        try:
            task_id = str(task.task_id)
            logger.info(f"🔧 [{self.agent_id}] Processing task: {task_id}")
            
            # Update task status to processing
            await r.hset(f"task:{task_id}", mapping={"status":"processing","role":ROLE})
            
            # Extract task details from payload
            description = task.payload.description or "No description provided"
            requirements = task.payload.requirements or []
            context = task.payload.context or {}
            tech_stack = context.get('tech_stack', [])
            
            # Fetch relevant context from vector store
            context_results = []
            if description:
                try:
                    context_results = search_by_text(description, limit=5)
                except Exception as e:
                    logger.warning(f"🔧 [{self.agent_id}] Context fetch error: {e}")
            
            # Prepare context for LLM
            context_text = "\n".join([
                f"- {result.get('content', '')[:200]}..." 
                for result in context_results
            ]) if context_results else "No relevant context found."
            
            # Generate backend implementation using LLM
            prompt = f"""You are an expert backend developer. Generate production-ready backend code.

Task Description: {description}
Requirements: {', '.join(requirements) if requirements else 'None specified'}
Tech Stack: {', '.join(tech_stack) if tech_stack else 'Python/FastAPI (default)'}

Relevant Context:
{context_text}

Generate:
1. API endpoints with proper error handling
2. Database models and migrations
3. Business logic with validation
4. Unit tests
5. Documentation

Ensure the code follows best practices for security, performance, and maintainability."""
            
            # Generate the backend implementation
            result = generate_markdown(prompt)
            
            # Create result message
            result_payload = ResultPayload(
                task_id=task.task_id,
                result=result,
                status="completed",
                metadata={
                    "agent_id": self.agent_id,
                    "processing_time": "calculated_time",
                    "context_items": len(context_results),
                    "tech_stack": tech_stack
                }
            )
            
            result_message = ResultMessage(
                task_id=task.task_id,
                agent_role=ROLE,
                payload=result_payload,
                correlation_id=task.correlation_id
            )
            
            # Publish result
            await self.message_handler.publish_message(
                message=result_message,
                headers={"task_id": task_id, "agent_id": self.agent_id}
            )
            
            # Store result in Redis
            await r.hset(f"task:{task_id}", mapping={"status":"done","result":result})
            logger.info(f"🔧 [{self.agent_id}] Task {task_id} completed")
            
        except Exception as e:
            await r.hset(f"task:{task_id}", mapping={"status":"error","error":str(e)})
            logger.error(f"❌ [{self.agent_id}] Task {task_id} failed: {e}")

async def main():
    agent = BackendDevAgent()
    await agent.initialize()
    
    # Subscribe to tasks with production message handler
    await agent.message_handler.subscribe_with_validation(
        subject=SUBJECT,
        handler=agent.handle_task_message,
        durable=f"{ROLE}_durable",
        queue=f"{ROLE}_queue"
    )
    
    logger.info(f"🔧 [{agent.agent_id}] Listening on {SUBJECT}")
    
    # Keep the agent running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info(f"🔧 [{agent.agent_id}] Shutting down gracefully")
    except Exception as e:
        logger.error(f"❌ [{agent.agent_id}] Unexpected error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())