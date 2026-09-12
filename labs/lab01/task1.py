"""Модуль аналізу надійності паролів (Завдання 1, Варіант 3)."""

import os
import random
import string
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.student import STUDENT_NAME, VARIANT_NUMBER

PASSWORDS = [
    "UserPass1!",
    "temp",
    "Cybersecurity",
    "guest",
    "P0w3rful@Pass",
    "login",
    "Defens3#2023",
    "abc123",
    "Elit3@Secur",
    "demo",
]
CRITERIA = {
    "min_length": 9,
    "require_digits": True,
    "require_upper": True,
    "require_special": True,
}
FORBIDDEN_PASSWORDS = {"temp", "guest", "login", "demo", "abc123", "user"}


def evaluate_password(password: str, all_passwords: list[str]) -> str:
    """Оцінює рівень надійності переданого пароля."""
    min_len = CRITERIA["min_length"]

    if password in FORBIDDEN_PASSWORDS or len(password) < min_len:
        return "Заборонений"

    has_digit = any(c.isdigit() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_spec = any(c in string.punctuation for c in password)

    all_criteria_met = len(password) >= min_len and has_digit and has_upper and has_spec

    if all_criteria_met:
        if len(password) >= min_len + 4 and all_passwords.count(password) == 1:
            return "Дуже сильний"
        return "Сильний"

    if len(password) >= min_len and (has_digit or has_upper or has_spec):
        return "Середній"

    if has_digit or has_upper or has_lower or has_spec:
        return "Слабкий"

    return "Заборонений"


def run_task1():
    """Головна функція для виконання першого завдання."""
    print(f"=== Завдання 1 | Студент: {STUDENT_NAME}, Варіант: {VARIANT_NUMBER} ===")
    passwords_list = PASSWORDS.copy()

    random.seed(42)
    sample_indices = random.sample(range(len(passwords_list)), 3)
    for idx in sample_indices:
        passwords_list.append(passwords_list[idx])

    print(f"{'№':<4} | {'Пароль':<20} | {'Оцінка'}")
    print("-" * 45)
    for idx, pwd in enumerate(passwords_list, 1):
        category = evaluate_password(pwd, passwords_list)
        print(f"{idx:<4} | {pwd:<20} | {category}")


if __name__ == "__main__":
    run_task1()
