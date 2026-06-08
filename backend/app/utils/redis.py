import os
import logging
import redis.asyncio as aioredis

logger = logging.getLogger("uvicorn.error")

class RedisClientManager:
    """
    Manages lifecycle parameters and execution threads for the asynchronous
    Redis connection pool inside the bare-metal cluster.
    """
    def __init__(self):
        # Fall back to localhost loopback if .env parsing fails
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: aioredis.Redis | None = None

    def initialize_pool(self) -> aioredis.Redis:
        """
        Instantiates a highly resilient Redis client backed by a persistent
        asynchronous connection pool.
        """
        logger.info(f"[REDIS_INIT] Spawning connection pool targeting: {self.redis_url}")
        
        # Connection pooling optimizes socket reuse under multi-agent load
        self.client = aioredis.from_url(
            self.redis_url,
            decode_responses=True,  # Automatically decodes raw bytes to UTF-8 strings
            max_connections=20,     # Caps persistent sockets to control host memory overhead
            socket_timeout=5.0      # Hard boundary to prevent thread stalling
        )
        return self.client

    async def close_pool(self):
        """Disconnects active sockets cleanly during system teardown."""
        if self.client:
            logger.info("[REDIS_SHUTDOWN] Severing active Redis connection pools...")
            await self.client.close()

# Export a single, global manager instance to preserve singleton architecture
redis_manager = RedisClientManager()