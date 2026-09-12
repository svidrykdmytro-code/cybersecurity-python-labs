"""Модуль безпечної автентифікації та логування (Завдання 3, Варіант 3)."""

import csv
import functools
import hashlib
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.student import STUDENT_NAME, VARIANT_NUMBER

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_PATH = os.path.join(DATA_DIR, "users.csv")
LOG_PATH = os.path.join(DATA_DIR, "log.json")

SALT = f"{VARIANT_NUMBER:05d}"
MIN_PASSWORD_LEN = 8


class ValidationError(Exception):
    """Помилка валідації вхідних даних пароля."""


def log_event(func):
    """Декоратор для логування подій автентифікації у JSON-файл."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        username = args[0] if args else kwargs.get("username", "unknown")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = "failure"

        try:
            res = func(*args, **kwargs)
            result = "success" if res else "failure"
            return res
        finally:
            log_record = {
                "event": "login",
                "user": username,
                "result": result,
                "timestamp": timestamp,
                "args": [str(a) for a in args],
                "kwargs": {k: str(v) for k, v in kwargs.items()},
            }
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
                logs = []
                if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 0:
                    with open(LOG_PATH, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                logs.append(log_record)
                with open(LOG_PATH, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=4, ensure_ascii=False)
            except (OSError, PermissionError) as exc:
                print(f"[Помилка логування]: {exc}")

    return wrapper


def generate_hash(password: str, salt: str = "00000") -> str:
    """Генерує хеш sha1 від комбінації пароля та солі."""
    if not password or not salt:
        raise ValueError("Пароль та сіль не можуть бути порожніми.")
    if len(password) < MIN_PASSWORD_LEN:
        raise ValidationError(
            f"Пароль має містити мінімум {MIN_PASSWORD_LEN} символів."
        )

    hasher = hashlib.sha1()
    hasher.update((password + salt).encode("utf-8"))
    return hasher.hexdigest()


def create_user(username: str, password: str) -> tuple[str, str]:
    """Створює запис користувача з персональною сіллю."""
    return username, generate_hash(password, SALT)


def create_users(users_list: tuple[tuple[str, str], ...]):
    """Зберігає список користувачів у CSV-файл."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CSV_PATH, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["username", "password_hash"])
        for username, pwd in users_list:
            user_entry = create_user(username, pwd)
            writer.writerow(user_entry)


def read_users_db() -> list[dict[str, str]]:
    """Зчитує дані користувачів із CSV-файлу."""
    users_db = []
    with open(CSV_PATH, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            users_db.append(row)
    return users_db


@log_event
def login(username: str, password: str) -> bool:
    """Виконує автентифікацію користувача."""
    if not username or not password:
        raise ValueError("Логін та пароль є обов'язковими для входу.")

    users_db = read_users_db()
    for row in users_db:
        if row["username"] == username:
            computed_hash = generate_hash(password, SALT)
            return row["password_hash"] == computed_hash
    return False


def run_task3():
    """Головна функція для запуску демонстрації третього завдання."""
    print(f"=== Завдання 3 | Студент: {STUDENT_NAME}, Варіант: {VARIANT_NUMBER} ===")

    users_to_register = (
        ("sec_officer", "P@ssword123"),
        ("analyst_01", "Secur1tyKey!"),
        ("dev_ninja", "CodeSafe#2026"),
        ("admin_root", "Sup3rRootPass"),
        ("help_operator", "HelpDesk@2026"),
        ("auditor_k", "Audit#Pass1"),
        ("trainee_bob", "Train33Pass!"),
        ("guest_temp", "Guest#Access1"),
        ("cloud_eng", "CloudS3cur3!"),
        ("soc_lead", "Mon1torCenter"),
    )

    try:
        print("\n1. Реєстрація користувачів та збереження у CSV...")
        create_users(users_to_register)

        print("\n2. Зчитування користувачів з бази:")
        db_entries = read_users_db()
        print(f"{'Username':<15} | {'SHA1 Hash'}")
        print("-" * 58)
        for entry in db_entries:
            print(f"{entry['username']:<15} | {entry['password_hash']}")

        print("\n3. Тестування автентифікації:")
        success_test = login("sec_officer", "P@ssword123")
        print(f"Вхід 'sec_officer' (вірний пароль): {success_test}")

        fail_test = login("sec_officer", "WrongPassword")
        print(f"Вхід 'sec_officer' (невірний пароль): {fail_test}")

        try:
            generate_hash("short", SALT)
        except ValidationError as exc:
            print(f"Тест валідації винятку: {exc}")

    except (OSError, FileNotFoundError, PermissionError) as exc:
        print(f"[Помилка файлової системи]: {exc}")
    except (ValidationError, ValueError) as exc:
        print(f"[Помилка валідації]: {exc}")


if __name__ == "__main__":
    run_task3()
