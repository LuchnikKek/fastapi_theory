import itertools
import logging
from functools import lru_cache
from typing import Optional, Any

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends

from src.db.elastic import get_elastic
from src.models.film import Film
from src.utils.formatters import SortFormatter, QueryFormatter
from src.utils.storages import get_redis_storage, RedisStorage

logger = logging.getLogger(__name__)


class FilmService:
    """Класс содержит бизнес-логику по работе с фильмами.

    Никакой магии тут нет. Обычный класс с обычными методами.
    Этот класс ничего не знает про DI.
    """

    sort_formatter = SortFormatter()
    query_formatter = QueryFormatter()

    def __init__(self, redis_storage: RedisStorage, elastic: AsyncElasticsearch):
        self.redis_storage = redis_storage
        self.elastic = elastic

    async def get_by_uuid(self, film_uuid: str) -> Optional[Film]:
        """Возвращает объект Фильма по UUID.

        Пытаемся получить данные из кеша `_film_from_cache`, потому что он работает быстрее.
        Если фильма нет в кеше, то ищем его в Elasticsearch через `_get_film_from_elastic`.
            и сохраняем фильм в кеш.
        Если он отсутствует в Elasticsearch, значит, фильма вообще нет в базе.

        Опционален, так как фильм может отсутствовать в базе
        """
        film = await self._get_film_from_redis(film_uuid)

        if not film:
            film = await self._get_film_from_elastic(film_uuid)
            if not film:
                return None
            await self.redis_storage.set_state(film.uuid, film.model_dump_json())

        return film

    async def _get_film_from_redis(self, film_uuid: str) -> Optional[Film]:
        film_data = await self.redis_storage.get_state(film_uuid)

        if film_data:
            return Film.model_validate_json(film_data)
        else:
            return None

    async def _get_film_from_elastic(self, film_uuid: str) -> Optional[Film]:
        """Пытаемся получить данные о фильме из хранилища ElasticSearch."""

        try:
            doc = await self.elastic.get(index="movies", id=str(film_uuid))
        except NotFoundError:
            return None
        return Film(**doc["_source"])

    @staticmethod
    async def _generate_record_key(record_number: int, sort: tuple[dict] = None, query: dict = None) -> str:
        return "movies/" + str(sort) + "/" + str(record_number) + "/" + str(query)

    async def _get_previous_record_search_after(
        self, record_number: int, sort: tuple[dict[str, Any]], query: dict
    ) -> Optional[list]:
        """Gets search_after value from ES.

        The itertools.chain.from_iterable is good here to transform a tuple of dicts to tuple of its keys.
        tuple(
            {key1: val1, key2: val2},
            {key3: val3},
            {key4: val4, key5: val5}
        ) -> tuple(key1, key2, key3, key4, key5)
        """
        include_only = tuple(itertools.chain.from_iterable(sort))

        data = await self.elastic.search(
            from_=record_number - 1,
            size=1,
            sort=sort,
            index="movies",
            source_includes=include_only,
            query=query,
            filter_path="hits.hits",
        )

        if data:
            return data["hits"]["hits"][0]["sort"]
        else:
            return None

    async def search_films_paginated(self, page_number: int, size: int, **kwargs) -> list[Film]:
        """The function which gets page number, size of page and optional kwargs.
        Returns the List of films from the related page.

        kwargs:
            search_query - A dict with {'field_to_search': 'value'} to fuzzy search.
            genre_uuid - A string uuid of Genre to filter films for.
            sort - A string name of field to make sort for. Default `asc`. Use: "-{sort}" for `desc`.

        Known issues: breaks at page_number=1000, size=1.
        """
        sort = self.sort_formatter.format(**kwargs)
        query = self.query_formatter.format(**kwargs)

        current_record_number = (page_number - 1) * size
        previous_record_key = await self._generate_record_key(current_record_number - 1, sort, query)

        search_after = None
        if current_record_number > 0:
            search_after = await self.redis_storage.get_state(previous_record_key)

            if not search_after:
                search_after = await self._get_previous_record_search_after(current_record_number, sort, query)
                await self.redis_storage.set_state(previous_record_key, search_after)

        films_data = await self.search_films_from_elastic(size, sort, query, search_after)
        return films_data

    async def search_films_from_elastic(
        self,
        size: int,
        sort: tuple[dict[str, Any]],
        query: dict[str, Any],
        search_after: dict[str, Any] = None,
    ) -> Optional[list[Film]]:
        """Gets films from elastic using search_after scroll.

        :param sort: A dict with sort params. Keys=fields, values=order. e.g. {'title': 'asc', 'description': 'desc'}.
        :param size: A size of page, count of returned records.
        :param query: A dict with Elastic query param.
        :param search_after: (Optional) A dict with search_after param. Keys=fields, values=values of record to start from.
        :return: A list of Films.
        """
        films = await self.elastic.search(
            search_after=search_after,
            index="movies",
            sort=sort,
            size=size,
            query=query,
            filter_path="hits.hits._source",
        )
        if not films:
            return None
        return [Film(**film["_source"]) for film in films["hits"]["hits"]]


@lru_cache()
def get_film_service(
    redis_storage: RedisStorage = Depends(get_redis_storage),
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(redis_storage, elastic)
