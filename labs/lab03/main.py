import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

from .config import APP_DESCRIPTION, APP_TITLE, APP_VERSION
from .database import initialize_database
from .repository import ConflictError, NotFoundError
from .routers import categories, records
from .schemas import StudentRead

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("lab03")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Створити відсутні таблиці під час запуску."""
    initialize_database()
    yield


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
)
app.include_router(categories.router)
app.include_router(records.router)


@app.exception_handler(NotFoundError)
def not_found_handler(request: Request, error: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)}
    )


@app.exception_handler(ConflictError)
def conflict_handler(request: Request, error: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)}
    )


@app.exception_handler(sqlite3.IntegrityError)
def integrity_handler(request: Request, error: sqlite3.IntegrityError) -> JSONResponse:
    logger.warning("Порушено обмеження бази: %s", error)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Дані порушують обмеження бази"},
    )


@app.exception_handler(sqlite3.Error)
def database_error_handler(request: Request, error: sqlite3.Error) -> JSONResponse:
    logger.exception("Помилка бази даних")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутрішня помилка сервера"},
    )


@app.get("/ping", tags=["service"], summary="Перевірка доступності API")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/student",
    response_model=StudentRead,
    tags=["service"],
    summary="Дані студента",
)
def student() -> StudentRead:
    return StudentRead(
        student_name=STUDENT_NAME,
        group_name=GROUP_NAME,
        variant_number=VARIANT_NUMBER,
    )
