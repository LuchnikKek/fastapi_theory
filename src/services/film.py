import itertools
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
from src.services.formatters import SortFormatter, QueryFormatter


class FilmService:
    """Класс содержит бизнес-логику по работе с фильмами.

    Никакой магии тут нет. Обычный класс с обычными методами.
    Этот класс ничего не знает про DI.
    """

    sort_formatter = SortFormatter()
    query_formatter = QueryFormatter()

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_uuid(self, film_uuid: str) -> Optional[Film]:
        """Возвращает объект Фильма по UUID.

        Пытаемся получить данные из кеша `_film_from_cache`, потому что он работает быстрее.
        Если фильма нет в кеше, то ищем его в Elasticsearch через `_get_film_from_elastic`.
            и сохраняем фильм в кеш.
        Если он отсутствует в Elasticsearch, значит, фильма вообще нет в базе.

        Опционален, так как фильм может отсутствовать в базе
        """
        film = await self._film_from_cache(film_uuid)

        if not film:
            film = await self._get_film_from_elastic(film_uuid)
            if not film:
                return None
            await self._put_film_to_cache(film)

        return film

    async def _get_film_from_elastic(self, film_uuid: UUID4) -> Optional[Film]:
        """Пытаемся получить данные о фильме из хранилища ElasticSearch."""

        try:
            doc = await self.elastic.get(index="movies", id=str(film_uuid))
        except NotFoundError:
            return None
        return Film(**doc["_source"])

    async def _film_from_cache(self, film_uuid: UUID4) -> Optional[Film]:
        """Пытаемся получить данные о фильме из кеша, используя команду get.

        Redis documentation: https://redis.io/commands/get/
        """
        data = await self.redis.get(str(film_uuid))
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
        await self.redis.set(str(film.uuid), film.model_dump_json(), FILM_CACHE_EXPIRE_IN_SECONDS)

    @staticmethod
    async def _generate_record_key(record_number: int, sort: dict = None, filter_query: dict = None) -> str:
        return "movies/" + str(sort) + "/" + str(record_number) + "/" + str(filter_query)

    async def _get_search_after_from_elastic(
        self, previous_record: int, sort: tuple[dict[str, Any]], filter_: dict
    ) -> Optional[list]:
        """Gets search_after value from ES.

        The itertools.chain.from_iterable is good here to transform a tuple of dicts to tuple of its keys.
        tuple(
            {key1: val1, key2: val2},
            {key3: val3},
            {key4: val4, key5: val5}
        ) -> tuple(key1, key2, key3, key4, key5)

        Raises IndexError: if previous_record >= count of records in index
        """
        if previous_record == -1:
            return None
        include_only = tuple(itertools.chain.from_iterable(sort)) if sort else None

        data = await self.elastic.search(
            from_=previous_record,
            size=1,
            index="movies",
            sort=sort,
            source_includes=include_only,
            query=filter_,
        )
        if sort == ({"_score": "desc"},):
            search_after = [data["hits"]["hits"][0]["_score"]]
        else:
            search_after = data["hits"]["hits"][0]["sort"]
        return search_after

    async def get_page(self, page_number: int, size: int, **kwargs) -> list[Film]:
        """The function which gets page number, size of page and optional kwargs.
        Returns the List of films from the related page.

        kwargs:
            search_query - A dict with {'field_to_search': 'value'} to fuzzy search.
            genre_uuid - A UUID4|str uuid of Genre to filter films for.
            sort - A str name of field to make sort for. Default `asc`. Use: "-{sort}" for `desc`.

        Known issues: breaks at page_number=1000, size=1.
        """
        sort_query = self.sort_formatter.format(**kwargs)
        query = self.query_formatter.format(**kwargs)

        previous_record_number = (page_number - 1) * size - 1
        previous_record_key = await self._generate_record_key(previous_record_number, sort_query, query)

        if await self._key_in_cache(previous_record_key):
            search_after = await self._get_search_after_from_cache(previous_record_key)
        else:
            try:
                search_after = await self._get_search_after_from_elastic(previous_record_number, sort_query, query)
            except IndexError:
                return []
            await self._put_search_after_to_cache(previous_record_key, search_after)

        films_data = await self._search_after_films_from_elastic(size, search_after, sort_query, query)

        future_search_after_key = await self._generate_record_key(previous_record_number + size, sort_query, query)

        if not await self._key_in_cache(future_search_after_key):
            await self._put_search_after_to_cache(future_search_after_key, films_data[-1]["sort"])

        return [Film(**film["_source"]) for film in films_data]

    async def _search_after_films_from_elastic(
        self,
        size: int,
        search_after: dict[str, Any],
        sort: tuple[dict[str, Any]],
        filter_query: dict[str, dict[str, str]],
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
