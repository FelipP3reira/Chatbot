from functools import lru_cache

from redis.asyncio import Redis

from app.config import obter_configuracao


@lru_cache(maxsize=1)
def obter_redis() -> Redis:
    return Redis.from_url(obter_configuracao().redis_url, decode_responses=True)
