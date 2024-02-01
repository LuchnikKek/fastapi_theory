from pydantic import BaseSettings


class TestSettings(BaseSettings):
    es_host: str = "http://elasticsearch:9200"
    es_index: str = "movies"
    es_id_field: str = "id"
    es_index_mapping: dict = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "actors": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {"id": {"type": "keyword"}, "name": {"type": "text"}},
                },
                "actors_names": {"type": "text"},
                "description": {"type": "text"},
                "directors": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {"id": {"type": "keyword"}, "name": {"type": "text"}},
                },
                "directors_names": {"type": "text"},
                "genre": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {"id": {"type": "keyword"}, "name": {"type": "text"}},
                },
                "id": {"type": "keyword"},
                "imdb_rating": {"type": "float"},
                "title": {
                    "type": "text",
                    "fields": {"raw": {"type": "keyword"}},
                },
                "writers": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {
                            "type": "text",
                        },
                    },
                },
                "writers_names": {"type": "text"},
            },
        }
    }

    redis_host: str = "http://redis:6379"
    service_url: str = "http://api:8000"


test_settings = TestSettings()
