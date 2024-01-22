from typing import Optional
from elasticsearch import AsyncElasticsearch

es: Optional[AsyncElasticsearch] = None


# Функция для внедрения зависимостей
async def get_elastic() -> AsyncElasticsearch:
    return es
