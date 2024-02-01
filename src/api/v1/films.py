from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse
from pydantic import UUID4

from src.api.v1.models.films import FilmShort, FilmLong
from src.services.film import FilmService, get_film_service

router = APIRouter()


@router.get("/", summary="Get films list", response_description="List of Film objects.")
async def films_all(
    page_number: Annotated[int, Query(description="Page number.", ge=1)] = 1,
    size: Annotated[int, Query(description="Page size.", ge=1, le=100)] = 10,
    sort: Annotated[
        str | None,
        Query(
            description='Sort field. By default sorts ascending. Use "-" to descending.',
            pattern="^-?imdb_rating$",
            example="-imdb_rating",
        ),
    ] = None,
    genre_uuid: Annotated[
        UUID4 | None,
        Query(description="Filter by genre. Takes UUID."),
    ] = None,
    film_service: FilmService = Depends(get_film_service),
) -> ORJSONResponse:
    records = await film_service.search_films_paginated(page_number, size, sort=sort, genre_uuid=genre_uuid)
    if not records:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Films not found.")

    films = [FilmShort(**film.model_dump()) for film in records]
    response_data = [film.model_dump() for film in films]
    response = {
        "data": {"type": "Array", "id": page_number, "data": response_data},
        "links": {"first": 1, "next": page_number + 1},
    }
    if page_number > 1:
        response["links"]["prev"] = page_number - 1
    return ORJSONResponse(response)


@router.get("/{film_uuid}", summary="Get Film by UUID", response_description="Film title and rating")
async def film_details(film_uuid: UUID4, film_service: FilmService = Depends(get_film_service)) -> ORJSONResponse:
    film = await film_service.get_by_uuid(str(film_uuid))

    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Film not found.")

    data = FilmLong(**film.model_dump())
    response = {"data": data.model_dump()}

    return ORJSONResponse(response)


@router.get("/search/{query}")
async def search_films(
    query: str,
    page_number: Annotated[int, Query(description="Page number.", ge=1)] = 1,
    size: Annotated[int, Query(description="Page size.", ge=1, le=100)] = 10,
    film_service: FilmService = Depends(get_film_service),
) -> ORJSONResponse:
    records = await film_service.search_films_paginated(page_number, size, search_query=("title", query))
    if not records:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Films not found.")

    films = [FilmShort(**film.model_dump()) for film in records]
    response_data = [film.model_dump() for film in films]
    response = {
        "data": {"type": "Array", "id": page_number, "data": response_data},
        "links": {"first": 1, "next": page_number + 1},
    }
    if page_number > 1:
        response["links"]["prev"] = page_number - 1
    return ORJSONResponse(response)


@router.get(
    "/similar/{film_uuid}", summary="Get similar Films by Film UUID", response_description="Film title and rating"
)
async def film_similar(film_uuid: UUID4, film_service: FilmService = Depends(get_film_service)) -> list[FilmShort]: ...
