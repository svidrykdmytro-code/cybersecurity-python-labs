import json
import logging
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

from . import repository
from .config import SEED_CATEGORIES, SEED_RECORDS
from .database import initialize_database
from .schemas import SeedData

SEED_PATH = Path(__file__).resolve().parent / "data" / "seed.json"

logger = logging.getLogger("lab03.seed")


def load_seed(path: Path = SEED_PATH) -> SeedData:
    """Прочитати та перевірити початкові дані."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    data = SeedData.model_validate(raw)
    if len(data.categories) != SEED_CATEGORIES or len(data.records) != SEED_RECORDS:
        raise ValueError(
            f"Очікується {SEED_CATEGORIES} категорії та {SEED_RECORDS} записів"
        )
    category_ids = {item.id for item in data.categories}
    if len(category_ids) != len(data.categories):
        raise ValueError("id категорій повторюються")
    if len({item.name for item in data.categories}) != len(data.categories):
        raise ValueError("Назви категорій повторюються")
    if len({item.code for item in data.records}) != len(data.records):
        raise ValueError("code записів повторюються")
    missing = {item.category_id for item in data.records} - category_ids
    if missing:
        raise ValueError(
            f"Записи посилаються на неіснуючі категорії: {sorted(missing)}"
        )
    return data


def seed() -> int:
    """Створити таблиці та заповнити порожню базу."""
    try:
        data = load_seed()
    except (OSError, json.JSONDecodeError) as error:
        logger.error("Не вдалося прочитати %s: %s", SEED_PATH.name, error)
        return 1
    except (ValidationError, ValueError) as error:
        logger.error("Некоректні початкові дані: %s", error)
        return 1

    try:
        initialize_database()
        if not repository.is_database_empty():
            print("База вже містить дані — заповнення пропущено, зміни не внесено.")
            return 0
        repository.seed_database(
            [item.model_dump() for item in data.categories],
            [item.model_dump() for item in data.records],
        )
    except (repository.NotFoundError, repository.ConflictError) as error:
        logger.error("Заповнення скасовано, жодних змін не збережено: %s", error)
        return 1
    except sqlite3.Error as error:
        logger.error("Помилка бази даних, зміни скасовано: %s", error)
        return 1

    print(
        f"Базу заповнено: {len(data.categories)} категорії, "
        f"{len(data.records)} записів."
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    sys.exit(seed())
