import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from src.core import config

app = FastAPI(
    # Название проекта, будет отображаться в документации
    title=config.PROJECT_NAME,
    # Адрес документации в красивом интерфейсе
    docs_url='/api/openapi',
    # Адрес документации в формате OpenAPI
    openapi_url='/api/openapi.json',
    # Замена стандартного JSON-сериализатора на более шуструю версию, написанную на Rust
    default_response_class=ORJSONResponse,
)

if __name__ == '__main__':
    # Приложение может запускаться командой
    # `uvicorn main:app --host 0.0.0.0 --port 8000`
    # но чтобы не терять возможность использовать дебагер,
    # запустим uvicorn сервер через python
    uvicorn.run(
        'main:app',
        host='0.0.0.0',
        port=8000,
    )
