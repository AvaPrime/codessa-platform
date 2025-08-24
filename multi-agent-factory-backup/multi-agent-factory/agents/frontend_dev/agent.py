import os, asyncio, json
from nats.aio.client import Client as NATS

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
ROLE     = os.getenv("AGENT_ROLE", "frontend_dev")
SUBJECT  = f"tasks.{ROLE}"

async def message_handler(msg):
    data = json.loads(msg.data.decode())
    task_id = data["task_id"]
    payload = data["payload"]

    print(f"[{ROLE}] Received task {task_id}: {payload}")

    # TODO: fetch context from memory + call LLM
    result_content = f"# Output from {ROLE}\n\n- Based on payload: {payload}"

    # Publish result
    result_subject = f"results.{ROLE}.{task_id}"
    result_data = { "task_id": task_id, "role": ROLE, "result": result_content }
    await msg._client.publish(result_subject, json.dumps(result_data).encode())
    print(f"[{ROLE}] Published result to {result_subject}")

async def main():
    nc = NATS()
    await nc.connect(NATS_URL)
    await nc.subscribe(SUBJECT, cb=message_handler)
    print(f"[{ROLE}] Listening on {SUBJECT} ...")
    # keep alive
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
    agent = FrontendDevAgent()
    print(f"🤖 {agent.role} agent ready")
 