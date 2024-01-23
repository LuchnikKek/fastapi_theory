from functools import lru_cache
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from src.db.elastic import get_elastic
from src.db.redis import get_redis
from src.models.film import Film

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут


class FilmService:
    """Класс содержит бизнес-логику по работе с фильмами.

    Никакой магии тут нет. Обычный класс с обычными методами.
    Этот класс ничего не знает про DI.
    """

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, film_id: str) -> Optional[Film]:
        """Возвращает объект Фильма по ID.

        Пытаемся получить данные из кеша `_film_from_cache`, потому что он работает быстрее.
        Если фильма нет в кеше, то ищем его в Elasticsearch через `_get_film_from_elastic`.
            и сохраняем фильм в кеш.
        Если он отсутствует в Elasticsearch, значит, фильма вообще нет в базе.

        Опционален, так как фильм может отсутствовать в базе
        """
        film = await self._film_from_cache(film_id)

        if not film:
            film = await self._get_film_from_elastic(film_id)
            if not film:
                return None
            await self._put_film_to_cache(film)

        return film

    async def _get_film_from_elastic(self, film_id: str) -> Optional[Film]:
        """Пытаемся получить данные о фильме из хранилища ElasticSearch."""

        try:
            doc = await self.elastic.get(index='movies', id=film_id)
        except NotFoundError:
            return None
        return Film(**doc['_source'])

    async def _film_from_cache(self, film_id: str) -> Optional[Film]:
        """Пытаемся получить данные о фильме из кеша, используя команду get.

        Redis documentation: https://redis.io/commands/get/
        """
        data = await self.redis.get(film_id)
        if not data:
            return None

        # pydantic предоставляет удобное API для создания объекта моделей из json
        film = Film.model_validate_json(data)
        return film

    async def _put_film_to_cache(self, film: Film):
        """
        Сохраняем данные о фильме, используя команду set.

        Выставляем время жизни кеша 5 минут
        https://redis.io/commands/set/
        pydantic позволяет сериализовать модель в json
        """
        await self.redis.set(film.id, film.model_dump_json(), FILM_CACHE_EXPIRE_IN_SECONDS)


@lru_cache()
def get_film_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    """Провайдер FilmService.

    С помощью Depends он сообщает, что ему необходимы Redis и Elasticsearch
    Для их получения мы ранее создали функции-провайдеры в модуле db

    Используем lru_cache-декоратор, чтобы создать объект сервиса в едином экземпляре (синглтона)
    """
    return FilmService(redis, elastic)
