#!/usr/bin/env python3
import asyncio
import argparse
import sys
from nats.aio.client import Client as NATS

async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--nats-url", default="nats://localhost:4222")
    p.add_argument("--from", dest="src", required=True, help="DLQ subject to read from")
    p.add_argument("--to", dest="dst", required=True, help="Main subject to publish to")
    args = p.parse_args()

    nc = NATS()
    await nc.connect(args.nats_url)
    js = nc.jetstream()

    async def handler(msg):
        await js.publish(args.dst, msg.data)
        await msg.ack()

    await js.subscribe(args.src, cb=handler, manual_ack=True, durable="dlq-replay")
    print(f"Replaying from {args.src} to {args.dst} ... Ctrl+C to stop")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
