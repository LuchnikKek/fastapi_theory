# Pet-проект FastAPI
Часть кода будет взята из курса от Яндекса. 
Часть задачек выдумаю сам.

_Just playground._

## Список реализованного

- Получение всех фильмов, детальной информации о конкретном.
- Нечёткий поиск по заголовку.
- Фильтр по жанру, сортировка по рейтингу.
- Модель `Film` для backend. Модели `FilmShort` и `FilmLong` для API.
- Пагинация через `search_after`.
- Единичные фильмы кэшируется в Redis по `UUID`.
- Пачки фильмов кэшируют сам курсор, что кратно экономит кэш. Ключ составной, из всех параметров. Коллизий не возникает.
- Контроль закрытия соединения с ES и Redis через `lifespan`.
- Провайдер `FilmService`, работающий с бизнес-логикой.
- Dependency Injection между вложенными объектами: **Ручки <-> FilmService <-> Elastic+Redis**.
- Dockerfile с poetry.

---

## API
Подробную документацию можно найти на `/api/openapi`.

#### Get all films

```http
  GET /api/v1/films
```

| Parameter     | Type   | Description                                    |
|:--------------|:-------|:-----------------------------------------------|
| `page_number` | `int`  | **Required**. Page number to paginate.         |
| `size`        | `int`  | **Required**. Count of films on page.          |
| `sort`        | `str`  | Sort query. Only asc/desc imdb_rating allowed. 
| `genre_uuid`   | `UUID4` | UUID of Genre to filter.                       |

#### Get film by id

```http
  GET /api/v1/films/{uuid}
```

| Parameter | Type  | Description                         |
|:----------|:------|:------------------------------------|
| `uuid`    | `str` | **Required**. UUID of film to fetch |

#### Find film by title

```http
  GET /api/v1/films/search/<title>
```

| Parameter     | Type   | Description                                    |
|:--------------|:-------|:-----------------------------------------------|
| `page_number` | `int`  | **Required**. Page number to paginate.         |
| `size`        | `int`  | **Required**. Count of films on page.          |
| `title`       | `str`  | **Required**. Film title to search. 

## Немного о работе API

При вызове ручка дёргает у своего Service (Провайдера) метод `get_by_uuid`. Метод в свою очередь возвращает `Film`.
Вся бизнес-логика обращений к базе, парсинга моделей, кэширования, обработки ошибок находится в `Service` классе.
Он возвращает либо `Film`, либо `None`. 
Получив ответ, ручка сама решает, как его распарсить и какую ошибку выбросить в случае `None`.

Ручка использует Service, Service использует соединения с ES и Redis. DI удаётся добиться благодаря `fastapi.Depends`.
Это класс, просто принимающий функцию. И возвращающий обратно её результат. 
Идея в том, что указывая его в сигнатуре класса, мы можем имплементировать эту функцию как угодно.
Можем возвращать классы и соединения по любой кастомной логике, не затрагивая при этом сами классы.
