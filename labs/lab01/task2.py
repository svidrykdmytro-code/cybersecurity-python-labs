"""Модуль контролю доступу (Завдання 2, Варіант 3)."""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.student import STUDENT_NAME, VARIANT_NUMBER

USERS = {
    "security_chief": {
        "role": "security_officer",
        "clearance": 4,
        "department": "Security",
        "active": True,
    },
    "network_admin": {
        "role": "network_admin",
        "clearance": 3,
        "department": "Network",
        "active": True,
    },
    "help_desk": {
        "role": "support",
        "clearance": 1,
        "department": "Support",
        "active": True,
    },
    "auditor_ext": {
        "role": "auditor",
        "clearance": 3,
        "department": "Audit",
        "active": True,
    },
    "temp_worker": {
        "role": "temporary",
        "clearance": 1,
        "department": "Temp",
        "active": False,
    },
}

RESOURCES = [
    ("incident_reports", 4),
    ("network_topology", 3),
    ("user_manual", 1),
    ("vulnerability_scans", 3),
    ("root_access", 4),
    ("help_tickets", 1),
    ("penetration_tests", 4),
    ("firewall_rules", 3),
    ("software_licenses", 2),
    ("faq_docs", 1),
]

SECURITY_LEVELS = ("Unrestricted", "Limited", "Sensitive", "Classified")
BLOCKED_USERS = {"temp_worker", "fired_employee", "compromised_acc"}


def check_access(username: str, resource_level: int) -> tuple[bool, str]:
    """Перевіряє доступ користувача до ресурсу відповідно до політики."""
    if username not in USERS:
        return False, "User not found"
    if username in BLOCKED_USERS:
        return False, "User is blocked"

    user_info = USERS[username]
    if not user_info.get("active", False):
        return False, "Account inactive"

    if user_info.get("clearance", 0) >= resource_level:
        return True, ""

    return False, "Insufficient clearance"


def run_task2():
    """Головна функція для виконання другого завдання."""
    print(f"=== Завдання 2 | Студент: {STUDENT_NAME}, Варіант: {VARIANT_NUMBER} ===")

    print("\n--- Список ресурсів системи ---")
    for res_name, lvl in RESOURCES:
        text_lvl = SECURITY_LEVELS[lvl - 1]
        print(f"Ресурс: {res_name:<22} | Рівень: {text_lvl} ({lvl})")

    print("\n--- Результати перевірки доступу ---")
    for user in USERS:
        for res_name, res_lvl in RESOURCES:
            allowed, reason = check_access(user, res_lvl)
            if allowed:
                print(f"user={user:<15} resource={res_name:<20} -> ALLOW")
            else:
                print(f"user={user:<15} resource={res_name:<20} -> DENY ({reason})")


if __name__ == "__main__":
    run_task2()
