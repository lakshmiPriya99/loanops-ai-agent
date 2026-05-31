import os

from redis import Redis
from rq import Queue


def redis_connection() -> Redis:
    return Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))


def agent_queue() -> Queue:
    return Queue("agent-runs", connection=redis_connection())
