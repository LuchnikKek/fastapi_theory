from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.services.film import FilmService, get_film_service

router = APIRouter()


class Film(BaseModel):
    """Модель Фильма для ответа API."""

    id: str
    title: str


# С помощью декоратора регистрируем обработчик film_details
# На обработку запросов по адресу <some_prefix>/film_id
# В сигнатуре функции указываем тип данных, получаемый из адреса запроса (film_id: str)
# Внедряем FilmService с помощью Depends(get_film_service)
# И указываем тип возвращаемого объекта — Film
@router.get('/{film_id}', response_model=Film)
async def film_details(film_id: str, film_service: FilmService = Depends(get_film_service)) -> Film:
    """Ручка получения информации о Фильме по id.

    Если фильм не найден, отдаём 404 статус.
    Стоит пользоваться уже определёнными HTTP-статусами, которые содержат enum.
        Такой код будет более поддерживаемым.

    Перекладываем нужные поля из models.Film в Film.
    У модели бизнес-логики есть поле description,
        Которое отсутствует в модели ответа API.
        Если бы использовалась общая модель для бизнес-логики и формирования ответов API
        мы бы предоставляли клиентам лишние данные,
        и, возможно, данные, которые опасно возвращать.
    """
    film = await film_service.get_by_id(film_id)

    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='film not found')

    return Film(id=film.id, title=film.title)
