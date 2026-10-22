from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import MAX_BULK_SIZE, VALUE_MAX, VALUE_MIN

Status = Literal["new", "in_progress", "done"]


class CategoryCreate(BaseModel):
    """Дані для створення категорії."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=40, examples=["drivers"])


class CategoryRead(BaseModel):
    """Категорія, повернена API."""

    id: int = Field(gt=0)
    name: str


class CategorySeed(CategoryCreate):
    """Категорія з початкового JSON із заданим id."""

    id: int = Field(gt=0)


class RecordCreate(BaseModel):
    """Дані для створення знахідки."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: str = Field(min_length=3, max_length=40, examples=["V03-TEST"])
    title: str = Field(min_length=3, max_length=120, examples=["Навчальна знахідка"])
    category_id: int = Field(gt=0, examples=[1])
    value: float = Field(
        ge=VALUE_MIN,
        le=VALUE_MAX,
        allow_inf_nan=False,
        description="Оцінка небезпеки, score (0–10)",
        examples=[7.5],
    )
    status: Status = Field(examples=["new"])


class RecordReplace(RecordCreate):
    """Повна заміна всіх змінюваних полів знахідки."""


class RecordRead(RecordCreate):
    """Знахідка разом з id та назвою категорії."""

    id: int = Field(gt=0)
    category_name: str


class StudentRead(BaseModel):
    """Дані студента."""

    student_name: str
    group_name: str
    variant_number: int


class SeedData(BaseModel):
    """Структура файлу seed.json."""

    model_config = ConfigDict(extra="forbid")

    categories: list[CategorySeed]
    records: list[RecordCreate]


class ErrorResponse(BaseModel):
    """Опис помилки."""

    detail: str


RecordBatch = Annotated[
    list[RecordCreate], Field(min_length=1, max_length=MAX_BULK_SIZE)
]
