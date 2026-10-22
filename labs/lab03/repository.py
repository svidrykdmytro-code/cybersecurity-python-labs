import sqlite3
from collections.abc import Iterable
from contextlib import closing
from typing import Any

from .database import get_connection

RECORD_COLUMNS = """
    SELECT r.id, r.code, r.title, r.category_id, c.name AS category_name,
           r.value, r.status
    FROM records AS r
    JOIN categories AS c ON c.id = r.category_id
"""


class NotFoundError(Exception):
    """Запис або категорію не знайдено."""


class ConflictError(Exception):
    """Порушено унікальність або категорія містить записи."""


def _connect() -> sqlite3.Connection:
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    return connection


def _category_exists(connection: sqlite3.Connection, category_id: int) -> bool:
    row = connection.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    return row is not None


def _fetch_record(connection: sqlite3.Connection, record_id: int) -> dict[str, Any]:
    row = connection.execute(
        f"{RECORD_COLUMNS} WHERE r.id = ?", (record_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError("Запис не знайдено")
    return dict(row)


def _unique_conflict(error: sqlite3.IntegrityError, message: str) -> Exception:
    if "UNIQUE" in str(error):
        return ConflictError(message)
    return error


def _insert_record(connection: sqlite3.Connection, data: dict[str, Any]) -> int:
    if not _category_exists(connection, data["category_id"]):
        raise NotFoundError(f"Категорію з id={data['category_id']} не знайдено")
    try:
        cursor = connection.execute(
            "INSERT INTO records (code, title, category_id, value, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                data["code"],
                data["title"],
                data["category_id"],
                data["value"],
                data["status"],
            ),
        )
    except sqlite3.IntegrityError as error:
        raise _unique_conflict(
            error, f"Запис з code '{data['code']}' вже існує"
        ) from error
    return cursor.lastrowid


def is_database_empty() -> bool:
    """Перевірити, що в обох таблицях немає даних."""
    with closing(_connect()) as connection:
        categories = connection.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        records = connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    return categories == 0 and records == 0


def count_records() -> int:
    """Повернути кількість записів."""
    with closing(_connect()) as connection:
        return connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]


def list_categories() -> list[dict[str, Any]]:
    """Повернути всі категорії за зростанням id."""
    with closing(_connect()) as connection:
        rows = connection.execute(
            "SELECT id, name FROM categories ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def create_category(name: str) -> dict[str, Any]:
    """Створити категорію."""
    with closing(_connect()) as connection:
        try:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name) VALUES (?)", (name,)
                )
        except sqlite3.IntegrityError as error:
            raise _unique_conflict(error, f"Категорія '{name}' вже існує") from error
        return {"id": cursor.lastrowid, "name": name}


def delete_category(category_id: int) -> None:
    """Видалити порожню категорію."""
    with closing(_connect()) as connection, connection:
        if not _category_exists(connection, category_id):
            raise NotFoundError("Категорію не знайдено")
        used = connection.execute(
            "SELECT COUNT(*) FROM records WHERE category_id = ?", (category_id,)
        ).fetchone()[0]
        if used:
            raise ConflictError("Категорія містить записи і не може бути видалена")
        try:
            connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        except sqlite3.IntegrityError as error:
            raise ConflictError(
                "Категорія містить записи і не може бути видалена"
            ) from error


def get_record(record_id: int) -> dict[str, Any]:
    """Повернути запис за id."""
    with closing(_connect()) as connection:
        return _fetch_record(connection, record_id)


def list_records(
    category_id: int | None = None,
    status: str | None = None,
    min_value: float | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Повернути записи з фільтрами та поділом на сторінки."""
    conditions: list[str] = []
    params: list[Any] = []
    if category_id is not None:
        conditions.append("r.category_id = ?")
        params.append(category_id)
    if status is not None:
        conditions.append("r.status = ?")
        params.append(status)
    if min_value is not None:
        conditions.append("r.value >= ?")
        params.append(min_value)
    if q is not None:
        conditions.append("instr(r.title, ?) > 0")
        params.append(q)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"{RECORD_COLUMNS}{where} ORDER BY r.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with closing(_connect()) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def create_record(data: dict[str, Any]) -> dict[str, Any]:
    """Створити запис."""
    with closing(_connect()) as connection:
        with connection:
            record_id = _insert_record(connection, data)
        return _fetch_record(connection, record_id)


def replace_record(record_id: int, data: dict[str, Any]) -> dict[str, Any]:
    """Повністю замінити змінювані поля запису."""
    with closing(_connect()) as connection:
        with connection:
            _fetch_record(connection, record_id)
            if not _category_exists(connection, data["category_id"]):
                raise NotFoundError(f"Категорію з id={data['category_id']} не знайдено")
            try:
                connection.execute(
                    "UPDATE records SET code = ?, title = ?, category_id = ?, "
                    "value = ?, status = ? WHERE id = ?",
                    (
                        data["code"],
                        data["title"],
                        data["category_id"],
                        data["value"],
                        data["status"],
                        record_id,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise _unique_conflict(
                    error, f"Запис з code '{data['code']}' вже існує"
                ) from error
        return _fetch_record(connection, record_id)


def delete_record(record_id: int) -> None:
    """Видалити запис."""
    with closing(_connect()) as connection, connection:
        cursor = connection.execute("DELETE FROM records WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            raise NotFoundError("Запис не знайдено")


def create_records_bulk(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Додати пакет записів в одній транзакції."""
    with closing(_connect()) as connection:
        with connection:
            ids = [_insert_record(connection, item) for item in items]
        return [_fetch_record(connection, record_id) for record_id in ids]


def seed_database(
    categories: Iterable[dict[str, Any]], records: Iterable[dict[str, Any]]
) -> None:
    """Заповнити порожню базу категоріями та записами в одній транзакції."""
    with closing(_connect()) as connection, connection:
        connection.executemany(
            "INSERT INTO categories (id, name) VALUES (?, ?)",
            [(item["id"], item["name"]) for item in categories],
        )
        for item in records:
            _insert_record(connection, item)
