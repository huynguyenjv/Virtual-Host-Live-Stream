import os

TIKTOK_LIVE_ID = os.getenv("TIKTOK_LIVE_ID", "demo_live_id")

QUEUE_TYPE = os.getenv("QUEUE_TYPE", "redis")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

RECONNECT_INTERVAL = int(os.getenv("RECONNECT_INTERVAL", 5))
