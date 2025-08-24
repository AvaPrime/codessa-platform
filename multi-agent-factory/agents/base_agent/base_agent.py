from config.settings import settings
import logging
import json

class BaseAgent:
    def __init__(self, role: str):
        self.role = role
        self.settings = settings
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, settings.observability.log_level.upper())
        )
        self.logger = logging.getLogger(f"agent.{role}")
        
        # Log configuration on startup
        self.logger.info(f"🤖 Agent {role} initializing")
        if settings.debug:
            config_dump = settings.dump_config()
            self.logger.info(f"Agent configuration: {json.dumps(config_dump, indent=2)}")
    
    async def connect_services(self):
        """Connect to external services using centralized settings"""
        # NATS connection
        self.nats_url = settings.nats.url
        
        # Redis connection
        self.redis_host = settings.redis.host
        self.redis_port = settings.redis.port
        
        # Database connection
        self.db_uri = settings.database.uri
        
        self.logger.info("✅ Service connections configured")

    async def connect(self):
        self.nc = await nats.connect(self.nats_url, max_reconnect_attempts=5, reconnect_time_wait=1)
        await self.nc.subscribe(self.subject, cb=self._on_msg)
        log.info("Subscribed to %s", self.subject)

    async def _on_msg(self, msg: nats.Msg):
        try:
            payload = json.loads(msg.data)
            await self.handle(payload)
            await msg.ack()
        except Exception:
            log.exception("Failed processing %s", msg.subject)
            if self.nc:
                await self.nc.publish(self.dlq_subject, msg.data)

    @abstractmethod
    async def handle(self, payload: Dict[str, Any]) -> None:
        ...

    async def run(self):
        await self.connect()
        while True:
            await asyncio.sleep(3600)
