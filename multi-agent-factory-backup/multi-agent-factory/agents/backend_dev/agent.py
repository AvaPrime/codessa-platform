import os, asyncio, json
import nats
import redis.asyncio as redis

NATS_URL   = os.getenv("NATS_URL", "nats://nats:4222")
ROLE       = os.getenv("AGENT_ROLE", "backend_dev")
SUBJECT    = f"tasks.{ROLE}"
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

async def main():
    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()

    async def handle(msg):
        data = json.loads(msg.data.decode())
        task_id = data["task_id"]
        payload = data["payload"]

        # set status: processing
        await r.hset(f"task:{task_id}", mapping={"status":"processing","role":ROLE})

        print(f"[{ROLE}] Received task {task_id}: {payload}")

        # TODO: fetch context + call LLM for real output
        result_content = f"# Output from {ROLE}\n\n- Based on payload: {payload}"

        # Publish result via JetStream
        result_subject = f"results.{ROLE}.{task_id}"
        await js.publish(result_subject, json.dumps({
            "task_id": task_id,
            "role": ROLE,
            "result": result_content
        }).encode())

        await msg.ack()  # tell JS we processed this message
        print(f"[{ROLE}] Published result to {result_subject}")

    # Durable + queue group = load-balanced & replayable
    await js.subscribe(SUBJECT, durable=ROLE, queue=ROLE, cb=handle, manual_ack=True)
    print(f"[{ROLE}] Listening on {SUBJECT} (durable={ROLE}, queue={ROLE}) ...")

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())