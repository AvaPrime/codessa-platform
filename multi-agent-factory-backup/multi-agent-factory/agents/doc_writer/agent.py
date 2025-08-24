import os, asyncio, json
import nats
import redis.asyncio as redis
from memory.vector_store import search_by_text
from llm.openai_helpers import generate_markdown

NATS_URL   = os.getenv("NATS_URL", "nats://nats:4222")
ROLE       = os.getenv("AGENT_ROLE", "doc_writer")
SUBJECT    = f"tasks.{ROLE}"
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def build_prompt(topic: str, ctx_items):
    bullets = "\n".join([f"- {c['id']} :: {c['metadata']}" for c in ctx_items]) or "- (no retrieved context)"
    return f"""Write a clear, enterprise-grade Markdown document about **{topic}**.
Use the relevant context below when helpful. Include a short intro, practical steps, and a final checklist.

Context:
{bullets}
"""

async def main():
    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()

    async def handle(msg):
        data = json.loads(msg.data.decode())
        task_id = data["task_id"]; payload = data["payload"]

        await r.hset(f"task:{task_id}", mapping={"status":"processing","role":ROLE})

        topic = payload.get("topic") or payload.get("title") or "Untitled"
        ctx = search_by_text(topic, k=5)
        prompt = build_prompt(topic, ctx)
        content = generate_markdown(prompt)

        result_subject = f"results.{ROLE}.{task_id}"
        await js.publish(result_subject, json.dumps({
            "task_id": task_id,
            "role": ROLE,
            "result": content
        }).encode())
        await msg.ack()
        print(f"[{ROLE}] Done {task_id} -> {result_subject}")

    await js.subscribe(SUBJECT, durable=ROLE, queue=ROLE, cb=handle, manual_ack=True)
    print(f"[{ROLE}] Listening on {SUBJECT} (durable={ROLE}, queue={ROLE}) ...")
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
