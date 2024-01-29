from functools import lru_cache
from typing import Optional, Any

import orjson
from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from pydantic import UUID4
from redis.asyncio import Redis
from redis.typing import KeyT

from src.core.config import FILM_CACHE_EXPIRE_IN_SECONDS
from src.db.elastic import get_elastic
from src.db.redis import get_redis
from src.models.film import Film


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

    async def _get_film_from_elastic(self, film_id: UUID4) -> Optional[Film]:
        """Пытаемся получить данные о фильме из хранилища ElasticSearch."""

        try:
            doc = await self.elastic.get(index="movies", id=str(film_id))
        except NotFoundError:
            return None
        return Film(**doc["_source"])

    async def _film_from_cache(self, film_id: UUID4) -> Optional[Film]:
        """Пытаемся получить данные о фильме из кеша, используя команду get.

        Redis documentation: https://redis.io/commands/get/
        """
        data = await self.redis.get(str(film_id))
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
        await self.redis.set(str(film.id), film.model_dump_json(), FILM_CACHE_EXPIRE_IN_SECONDS)

    @staticmethod
    async def _get_previous_record_number(page_number: int, size: int) -> int:
        return (page_number - 1) * size - 1

    @staticmethod
    async def _generate_record_key(record_number: int, sort: dict = None, filter_query: dict = None) -> str:
        return "movies/" + str(sort) + "/" + str(record_number) + "/" + str(filter_query)

    async def _get_search_after_from_elastic(
        self, previous_record: int, sort: dict[str, Any], filter_query: dict
    ) -> Optional[list]:
        """
        Raises IndexError: if previous_record >= count of records in index
        """
        if previous_record == -1:
            return None

        data = await self.elastic.search(
            from_=previous_record,
            size=1,
            index="movies",
            sort=sort,
            source_includes=tuple(sort.keys()),
            query=filter_query,
        )
        search_after = data["hits"]["hits"][0]["sort"]
        return search_after

    @staticmethod
    async def _format_sort_query(sort_q: str) -> dict[str, str]:
        if sort_q:
            return {"imdb_rating": "desc" if sort_q.startswith("-") else "asc"}
        else:
            return {"id": "asc"}

    @staticmethod
    async def _format_filter_query(filter_q: UUID4) -> dict:
        query = {"nested": {"path": "genre", "query": {"term": {"genre.id": str(filter_q)}}}}
        return query

    async def get_page(self, page_number: int, size: int, sort_q=None, filter_q=None) -> list[Film]:
        """Не работает при page_number = 1000, size = 1"""
        sort_query = await self._format_sort_query(sort_q)
        filter_query = None
        if filter_q:
            filter_query = await self._format_filter_query(filter_q)

        previous_record_number = await self._get_previous_record_number(page_number, size)
        previous_record_key = await self._generate_record_key(previous_record_number, sort_query, filter_query)

        if await self._key_in_cache(previous_record_key):
            search_after = await self._get_search_after_from_cache(previous_record_key)
        else:
            try:
                search_after = await self._get_search_after_from_elastic(
                    previous_record_number, sort_query, filter_query
                )
            except IndexError:
                return []
            await self._put_search_after_to_cache(previous_record_key, search_after)

        films_data = await self._search_after_films_from_elastic(size, search_after, sort_query, filter_query)

        future_search_after_number = await self._get_previous_record_number(page_number + 1, size)
        future_search_after_key = await self._generate_record_key(future_search_after_number, sort_query, filter_query)

        if not await self._key_in_cache(future_search_after_key):
            await self._put_search_after_to_cache(future_search_after_key, films_data[-1]["sort"])

        return [Film(**film["_source"]) for film in films_data]

    async def _search_after_films_from_elastic(
        self, size: int, search_after: dict[str, Any], sort: dict[str, Any], filter_query: dict[str, dict[str, str]]
    ) -> Optional[list[Film]]:
        """Gets films from elastic using search_after scroll.

        :param sort: A dict with sort params. Keys=fields, values=order. e.g. {'title': 'asc', 'description': 'desc'}.
        :param size: A size of page, count of returned records.
        :param search_after: A dict with search_after param. Keys=fields, values=values of record to start from.
        :return: A list of Films.
        """
        films = await self.elastic.search(
            search_after=search_after, index="movies", sort=sort, size=size, query=filter_query
        )
        films_data = [film for film in films["hits"]["hits"]]

        return films_data

    async def _key_in_cache(self, key: KeyT) -> bool:
        """Checks if the key in cache.

        :param key: A key to check.
        :return: True if key contains record, else False.
        """
        return await self.redis.exists(key)

    async def _get_search_after_from_cache(self, key: str) -> Optional[dict[str, Any]]:
        """Gets value of previous record from cache.

        :param key: A string key.
        :return: A dict `search_after`.
        """
        cursor = await self.redis.get(key)

        if not cursor:
            return None

        return orjson.loads(cursor)

    async def _put_search_after_to_cache(self, key, value: list) -> None:
        """Puts `search_after` value in cache.

        :param key: A string key.
        :param value: A dict `search_after` for key.
        :return: None.
        """
        value_str = orjson.dumps(value)
        await self.redis.set(key, value_str, FILM_CACHE_EXPIRE_IN_SECONDS)


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
