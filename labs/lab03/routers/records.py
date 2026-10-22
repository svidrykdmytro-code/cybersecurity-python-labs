from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, status

from .. import repository
from ..config import DEFAULT_LIMIT, MAX_LIMIT, VALUE_MAX, VALUE_MIN
from ..schemas import (
    ErrorResponse,
    RecordBatch,
    RecordCreate,
    RecordRead,
    RecordReplace,
    Status,
)

router = APIRouter(prefix="/records", tags=["records"])

RecordId = Annotated[int, Path(gt=0, description="id запису (додатне ціле)")]

NOT_FOUND = {
    404: {"model": ErrorResponse, "description": "Запис або категорію не знайдено"}
}
CONFLICT = {409: {"model": ErrorResponse, "description": "code вже існує"}}


@router.get(
    "",
    response_model=list[RecordRead],
    summary="Список знахідок із фільтрами",
    description="Фільтри об’єднуються через AND, результат відсортовано за id.",
)
def list_records(
    category_id: Annotated[
        int | None, Query(gt=0, description="Лише записи цієї категорії")
    ] = None,
    status_filter: Annotated[
        Status | None, Query(alias="status", description="Лише записи з цим статусом")
    ] = None,
    min_value: Annotated[
        float | None,
        Query(ge=VALUE_MIN, le=VALUE_MAX, description="value >= min_value (0–10)"),
    ] = None,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=120, description="Підрядок у title"),
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=MAX_LIMIT, description="Кількість записів (1–100)")
    ] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0, description="Кількість пропущених")] = 0,
) -> list[dict]:
    return repository.list_records(
        category_id=category_id,
        status=status_filter,
        min_value=min_value,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{record_id}",
    response_model=RecordRead,
    summary="Одна знахідка",
    responses=NOT_FOUND,
)
def get_record(record_id: RecordId) -> dict:
    return repository.get_record(record_id)


@router.post(
    "",
    response_model=RecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити знахідку",
    responses={**NOT_FOUND, **CONFLICT},
)
def create_record(payload: RecordCreate) -> dict:
    return repository.create_record(payload.model_dump())


@router.post(
    "/bulk",
    response_model=list[RecordRead],
    status_code=status.HTTP_201_CREATED,
    summary="Пакетне створення (одна транзакція)",
    description="Зберігає всі записи пакета (1–100) або жодного.",
    responses={**NOT_FOUND, **CONFLICT},
)
def create_records_bulk(payload: Annotated[RecordBatch, Body()]) -> list[dict]:
    return repository.create_records_bulk(item.model_dump() for item in payload)


@router.put(
    "/{record_id}",
    response_model=RecordRead,
    summary="Повна заміна змінюваних полів",
    responses={**NOT_FOUND, **CONFLICT},
)
def replace_record(record_id: RecordId, payload: RecordReplace) -> dict:
    return repository.replace_record(record_id, payload.model_dump())


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити знахідку",
    responses=NOT_FOUND,
)
def delete_record(record_id: RecordId) -> None:
    repository.delete_record(record_id)
