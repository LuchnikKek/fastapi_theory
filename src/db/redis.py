from typing import Optional
from redis.asyncio import Redis

redis: Optional[Redis] = None


# Функция для внедрения зависимостей
async def get_redis() -> Redis:
    return redis
