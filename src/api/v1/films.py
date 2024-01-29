from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, UUID4

from src.services.film import FilmService, get_film_service

router = APIRouter()


class Film(BaseModel):
    """Модель Фильма для ответа API."""

    type: str = "Film"
    id: UUID4
    title: str
    imdb_rating: float = 0.0


@router.get("/", summary="Get films list.", response_description="List of Film objects.")
async def films_all(
    page_number: Annotated[int, Query(description="Page number.", ge=1)] = 1,
    size: Annotated[int, Query(description="Page size.", ge=1, le=100)] = 10,
    sort: Annotated[
        str | None,
        Query(
            description='Sort field. By default sorts ascending. Use "-" to descending.',
            pattern="^-?imdb_rating$",
            example="imdb_rating",
        ),
    ] = None,
    genre_uuid: Annotated[
        UUID4 | None,
        Query(description="Filter by genre. Takes UUID."),
    ] = None,
    film_service: FilmService = Depends(get_film_service),
) -> dict:

    records = await film_service.get_page(page_number, size, sort, genre_uuid)
    films = [Film(id=film.id, title=film.title, imdb_rating=film.imdb_rating) for film in records]
    response_data = [film.model_dump() for film in films]
    response = {
        "data": {"type": "Array", "id": page_number, "data": response_data},
        "links": {"first": 1, "next": page_number + 1},
    }
    if page_number > 1:
        response["links"]["prev"] = page_number - 1
    return response


@router.get("/{film_id}", summary="Get Film by ID", response_description="Film title and rating")
async def film_details(film_id: UUID4, film_service: FilmService = Depends(get_film_service)) -> Film:
    film = await film_service.get_by_id(film_id)

    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Film not found.")

    return Film(id=film.id, title=film.title)


@router.get("/similar/{film_id}", summary="Get similar Films by Film ID", response_description="Film title and rating")
async def film_similar(film_id: UUID4, film_service: FilmService = Depends(get_film_service)) -> list[Film]:
    pass
