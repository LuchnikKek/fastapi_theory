import orjson

from pydantic import BaseModel, UUID4


def orjson_dumps(v, *, default) -> str:
    """orjson.dumps возвращает bytes, а pydantic требует unicode, поэтому декодируем."""
    return orjson.dumps(v, default=default).decode()


class Film(BaseModel):
    """Внутренняя модель Фильма, использующаяся только в рамках бизнес-логики.

    Мы уже создавали одну модель, но она использовалась только в рамках API
    """
    id: UUID4
    title: str
    description: str = None
    imdb_rating: float = 0.0

    class Config:
        """Заменяем стандартную работу с json на более быструю."""
        json_loads = orjson.loads
        json_dumps = orjson_dumps
