#!/usr/bin/env python3
"""Temporal worker service for Multi-Agent Factory"""

import asyncio
import signal
import sys
from orchestrator.temporal_client import temporal_manager

async def main():
    """Main worker process"""
    print("🚀 Starting Multi-Agent Factory Temporal Worker...")
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        print(f"\n📡 Received signal {signum}, shutting down gracefully...")
        asyncio.create_task(temporal_manager.close())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the worker (this will run indefinitely)
        await temporal_manager.start_worker()
    except KeyboardInterrupt:
        print("\n🛑 Worker interrupted by user")
    except Exception as e:
        print(f"❌ Worker failed: {e}")
        raise
    finally:
        await temporal_manager.close()
        print("✅ Worker shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())