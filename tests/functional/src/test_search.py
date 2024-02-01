import uuid

import aiohttp
import pytest
from elasticsearch import AsyncElasticsearch
from functional.settings import test_settings


#  Название теста должно начинаться со слова `test_`
#  Любой тест с асинхронными вызовами нужно оборачивать декоратором `pytest.mark.asyncio`, который следит за запуском и работой цикла событий.


@pytest.mark.asyncio
async def test_search():

    # 1. Генерируем данные для ES
    es_data = [
        {
            "id": str(uuid.uuid4()),
            "imdb_rating": 8.5,
            "title": "The Star",
            "description": "New World",
            "actors_names": ["Ann", "Bob"],
            "writers_names": ["Ben", "Howard"],
            "directors_names": ["Bryan", "Harry"],
            "actors": [
                {"id": "ef86b8ff-3c82-4d31-ad8e-72b69f4e3f95", "name": "Ann"},
                {"id": "fb111f22-121e-44a7-b78f-b19191810fbf", "name": "Bob"},
            ],
            "writers": [
                {"id": "caf76c67-c0fe-477e-8766-3ab3ff2574b5", "name": "Ben"},
                {"id": "b45bd7bc-2e16-46d5-b125-983d356768c6", "name": "Howard"},
            ],
            "directors": [
                {"id": "9107c550-bdce-40a1-9f84-3a9daa0bf584", "name": "Bryan"},
                {"id": "bfc3c484-e30e-40fd-afd0-7d2cac8bbe31", "name": "Harry"},
            ],
            "genre": [
                {"id": "72ac03e4-cd5d-40af-b190-f1cb2f19f5a2", "name": "Action"},
                {"id": "61e08d13-e169-4a77-b286-458e66f1fb27", "name": "Sci-Fi"},
            ],
        }
        for _ in range(60)
    ]

    bulk_query: list[dict] = []
    for row in es_data:
        data = {"_index": "movies", "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    # 2. Загружаем данные в ES
    es_client = AsyncElasticsearch(hosts=test_settings.es_host)

    await es_client.close()

    # 3. Запрашиваем данные из ES по API

    session = aiohttp.ClientSession()
    url = test_settings.service_url + "/api/v1/films/search"
    query_data = {"query": "The Star"}
    async with session.get(url, params=query_data) as response:
        body = await response.json()
        headers = response.headers
        status = response.status
    await session.close()

    # 4. Проверяем ответ
    print(body)
    print(headers)
    assert status == 200
    assert len(body) == 2
