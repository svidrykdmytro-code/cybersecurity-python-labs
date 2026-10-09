# Лабораторна робота №2 — Варіант 3

**Валідатор та аналізатор конфігурацій правил фаєрвола**

Студент: Свідрик Д. М., група КБ-202

## Встановлення

З кореня репозиторію:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Структура файлів

```
labs/lab02/
├── __init__.py
├── main.py                      # команди demo та analyze
├── task1.py                     # Завдання 1: класи User, Admin, Session, AuditLog, UserAccount
├── task2.py                     # Завдання 2: аудит правил фаєрвола
├── README.md
└── data/
    └── firewall_rules.json      # вхідні дані з lab2_data.zip (каталог data_v03)
```

Після запуску `analyze` у `data/` створюються:

- `fw_audit_report.json` — звіт аудиту;
- `firewall_rules_clean.json` — очищений список правил;
- `fw_audit.log` — журнал аудиту.

## Запуск

Завдання 1 (демонстрація ООП):

```
python -m labs.lab02.main demo
```

Завдання 2 (аудит правил):

```
python -m labs.lab02.main analyze --check-conflicts
python -m labs.lab02.main analyze --rules-file labs/lab02/data/firewall_rules.json --output labs/lab02/data/fw_audit_report.json --check-conflicts --log-level DEBUG
```

## Створення ще одного адміністратора (вручну)

Запустити інтерпретатор Python з кореня репозиторію:

```
python
```

```python
from labs.lab02.task1 import Admin, UserAccount
a = Admin("admin2", "admin_two@lpnu.ua", ["read_logs"], password="Pass#2026")
print(a)
a.grant_permission("edit_firewall")
print(a)
acc = UserAccount(a)
acc.login("admin2", "Pass#2026", "10.0.0.5")
acc.login("admin2", "wrong", "10.0.0.5")
acc.audit_log.show_all()
exit()
```

## Параметри CLI (`analyze`)

| Параметр | Опис | За замовчуванням |
|---|---|---|
| `--rules-file` | файл правил (`.json` або `.csv`) | `data/firewall_rules.json` |
| `--output` | JSON-звіт аудиту | `data/fw_audit_report.json` |
| `--clean-output` | очищений список правил | `data/firewall_rules_clean.json` |
| `--check-conflicts` | прапорець: шукати конфлікти ALLOW/DENY | вимкнено |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `--audit-log` | файл журналу аудиту | `data/fw_audit.log` |

## Поведінка при помилках

- файл правил не існує — `[ERROR] Rules file not found`, код виходу 1;
- пошкоджений JSON — `[ERROR] Malformed JSON`, код виходу 1;
- непідтримуваний формат файлу — `[ERROR] Cannot read ...`, код виходу 1;
- окремий пошкоджений запис — пропускається з `[ERROR] Skipped malformed entry`, аналіз триває;
- некоректні IP, маски, порти або дії — правило відхиляється з `[WARNING]` і не потрапляє до очищеного списку.

## Перевірка коду

```
ruff check .
ruff format --check .
```
