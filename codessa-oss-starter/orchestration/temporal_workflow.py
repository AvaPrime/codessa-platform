# Temporal workflow shell that wraps a LangGraph run
from temporalio import workflow

@workflow.defn
class AgentRun:
    @workflow.run
    async def run(self, task: dict) -> dict:
        # TODO: call into your LangGraph runtime; add retries via Temporal config
        return {"ok": True, "echo": task}
