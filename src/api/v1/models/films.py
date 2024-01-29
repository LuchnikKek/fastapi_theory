"""Models for API v1."""

from typing import Optional

from pydantic import Field

from src.models.mixins import TypedMixin, UUIDMixin


class PersonInline(TypedMixin, UUIDMixin):
    full_name: str = Field(alias="name")


class ActorInline(PersonInline):
    pass


class WriterInline(PersonInline):
    pass


class DirectorInline(PersonInline):
    pass


class GenreInline(TypedMixin, UUIDMixin):
    name: str


class FilmLong(TypedMixin, UUIDMixin):
    title: str
    description: Optional[str] = None
    imdb_rating: float = 0.0
    genre: list[GenreInline]
    actors: Optional[list[ActorInline]] = None
    writers: Optional[list[WriterInline]] = None
    directors: Optional[list[DirectorInline]] = None


class FilmShort(TypedMixin, UUIDMixin):
    title: str
    imdb_rating: float = 0.0
