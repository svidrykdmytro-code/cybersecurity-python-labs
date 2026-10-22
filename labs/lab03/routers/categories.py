from typing import Annotated

from fastapi import APIRouter, Path, status

from .. import repository
from ..schemas import CategoryCreate, CategoryRead, ErrorResponse

router = APIRouter(prefix="/categories", tags=["categories"])

CategoryId = Annotated[int, Path(gt=0, description="id категорії (додатне ціле)")]


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Список категорій",
    description="Повертає всі категорії за зростанням id.",
)
def list_categories() -> list[dict]:
    return repository.list_categories()


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Створити категорію",
    responses={409: {"model": ErrorResponse, "description": "Назва вже існує"}},
)
def create_category(payload: CategoryCreate) -> dict:
    return repository.create_category(payload.name)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити порожню категорію",
    responses={
        404: {"model": ErrorResponse, "description": "Категорію не знайдено"},
        409: {"model": ErrorResponse, "description": "Категорія містить записи"},
    },
)
def delete_category(category_id: CategoryId) -> None:
    repository.delete_category(category_id)
