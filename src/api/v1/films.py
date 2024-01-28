from http import HTTPStatus
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, UUID4
from src.services.film import FilmService, get_film_service

router = APIRouter()


class Film(BaseModel):
    """Модель Фильма для ответа API."""

    id: UUID4
    title: str
    imdb_rating: Optional[float] = 0.0


@router.get('/{film_id}',
            summary='Получение фильма по ID',
            response_description="Название и рейтинг фильма",)
async def film_details(film_id: UUID4, film_service: FilmService = Depends(get_film_service)) -> Film:
    """Ручка получения информации о Фильме по id."""
    film = await film_service.get_by_id(film_id)

    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='film not found')

    return Film(id=film.id, title=film.title)


@router.get('/',
            response_model=list[Film],
            summary='Получение списка фильмов',
            response_description="Название и рейтинг фильма",)
async def films_all(
        page_number: Annotated[int, Query(ge=1)],
        size: Annotated[int, Query(ge=1, le=100)],
        sort: Annotated[
            str, Query(pattern="^-?imdb_rating$", description="Sort field. Use \"-\" for inverse sort.")
        ] = None,
        film_service: FilmService = Depends(get_film_service),
) -> list[Film]:
    """Ручка получения информации о Фильмах."""

    if sort:
        sort_query = {'imdb_rating': 'desc' if sort.startswith('-') else 'asc'}
    else:
        sort_query = None

    films = await film_service.get_page(page_number, size, sort_query)

    return [Film(id=film.id, title=film.title, imdb_rating=film.imdb_rating) for film in films]
