FROM python:3.11-slim

WORKDIR /app

ARG API_PORT
ENV API_PORT=$API_PORT
EXPOSE $API_PORT

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY poetry.lock pyproject.toml /app/

RUN python -m pip install --no-cache-dir poetry==1.7.1 \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi \
    && rm -rf $(poetry config cache-dir)/{cache,artifacts}

ENTRYPOINT gunicorn src.main:app --bind api:8000 -k uvicorn.workers.UvicornWorker --reload
#ENTRYPOINT uvicorn src.main:app --host api --port $API_PORT --reload
