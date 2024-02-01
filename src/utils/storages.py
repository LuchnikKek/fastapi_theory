import abc
import logging
from functools import lru_cache
from typing import Any

from fastapi import Depends
from orjson import orjson
from redis.asyncio import Redis

from src.core.config import FILM_CACHE_EXPIRE_IN_SECONDS
from src.db.redis import get_redis

logger = logging.getLogger(__name__)


class BaseStorage(abc.ABC):
    """Base interface of storage."""

    @abc.abstractmethod
    def set_state(self, key: str, value: Any) -> None:
        """Set state for key."""

    @abc.abstractmethod
    def get_state(self, key: str) -> Any:
        """Get state from key."""


class RedisStorage(BaseStorage):
    """Class of Redis storage."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def set_state(self, key: str, value: Any) -> None:
        """Set state to key."""
        value_str = orjson.dumps(value)
        await self.redis.set(key, value_str, FILM_CACHE_EXPIRE_IN_SECONDS)

    async def get_state(self, key: str) -> Any:
        cursor = await self.redis.get(key)

        if not cursor:
            return None

        value = orjson.loads(cursor)
        logger.info("Object key=%s retrieved from cache. Value: %s", key, value)
        return value


@lru_cache()
def get_redis_storage(
    redis: Redis = Depends(get_redis),
) -> RedisStorage:
    """Провайдер FilmService.

    С помощью Depends он сообщает, что ему необходимы Redis и Elasticsearch
    Для их получения мы ранее создали функции-провайдеры в модуле db

    Используем lru_cache-декоратор, чтобы создать объект сервиса в едином экземпляре (синглтона)
    """
    return RedisStorage(redis)
