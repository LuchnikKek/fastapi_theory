from typing import Optional
from redis.asyncio import Redis

redis: Optional[Redis] = None


async def get_redis() -> Redis:
    """Функция для внедрения зависимостей."""

    return redis
