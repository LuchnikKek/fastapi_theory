import os
from logging import config as logging_config

from src.core.logger import LOGGING

# Применяем настройки логирования
logging_config.dictConfig(LOGGING)

# Название проекта, используется в Swagger-документации
PROJECT_NAME = os.getenv('PROJECT_NAME', 'movies')

# Настройки Redis
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5

# Настройки Elasticsearch
ELASTIC_HOST = os.getenv('ES_HOST', '127.0.0.1')
ELASTIC_PORT = int(os.getenv('ES_PORT', 9200))

# Корень проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

