"""Mixins."""

from functools import cached_property

import orjson
from pydantic import BaseModel, UUID4, Field, computed_field, ConfigDict


def orjson_dumps(v, *, default) -> str:
    """orjson.dumps возвращает bytes, а pydantic требует unicode, поэтому декодируем."""
    return orjson.dumps(v, default=default).decode()


class TypedMixin(BaseModel):
    @computed_field
    @cached_property
    def type(self) -> str:
        return self.__class__.__name__


class UUIDMixin(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    uuid: UUID4 = Field(alias="id")
