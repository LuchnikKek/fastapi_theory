"""Backend Model for Film."""

from typing import Optional

from pydantic import Field

from src.models.mixins import UUIDMixin


class PersonInline(UUIDMixin):
    full_name: str = Field(alias="name")


class ActorInline(PersonInline):
    pass


class WriterInline(PersonInline):
    pass


class DirectorInline(PersonInline):
    pass


class GenreInline(UUIDMixin):
    name: str


class Film(UUIDMixin):
    """Movie model used only within business-logic."""

    title: str
    description: Optional[str] = None
    imdb_rating: float = 0.0
    genre: list[GenreInline]
    actors: Optional[list[ActorInline]] = None
    writers: Optional[list[WriterInline]] = None
    directors: Optional[list[DirectorInline]] = None
