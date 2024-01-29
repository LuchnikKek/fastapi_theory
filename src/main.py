import logging
from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis

from src.api.v1 import films
from src.core import config
from src.core.logger import LOGGING
from src.db import elastic, redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis.redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)
    elastic.es = AsyncElasticsearch(hosts=[f"http://{config.ELASTIC_HOST}:{config.ELASTIC_PORT}"])
    yield
    # Отключаемся от баз при выключении сервера
    await redis.redis.close()
    await elastic.es.close()


app = FastAPI(
    title="Read-only API for online Cinema.",
    description="Information about films, genres and people involved in the creation.",
    version="0.0.2",
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    debug=True,
    log_config=LOGGING,
    log_level=logging.DEBUG,
)

app.include_router(films.router, prefix="/api/v1/films", tags=["Films"])
