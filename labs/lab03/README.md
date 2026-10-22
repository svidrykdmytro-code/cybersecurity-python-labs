# Лабораторна робота №3 — Варіант 3

**Реєстр вразливостей робочих станцій** (FastAPI + SQLite)

Студент: Свідрик Д. М., група КБ-202

## Предметна область

Сервіс обліку знахідок перевірки робочих станцій.

| Поле | Значення |
|---|---|
| `categories` | тип програмного забезпечення: `os`, `browser`, `office` |
| `code` | унікальний код знахідки, наприклад `V03-01` |
| `title` | назва знахідки, наприклад `Знахідка станції 01` |
| `value` | навчальна оцінка небезпеки, `float` від 0 до 10, одиниця `score` |
| `status` | стан опрацювання: `new`, `in_progress`, `done` |
| поріг | `8.0` — знахідки з `value >= 8.0` вважаються критичними |

## Встановлення

З кореня репозиторію:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Структура

```
labs/lab03/
├── __init__.py
├── main.py           # FastAPI-застосунок, /ping, /student, обробка помилок
├── database.py       # з’єднання та створення таблиць зі schema.sql
├── schema.sql        # готова схема (categories + records, варіанти 1–3)
├── repository.py     # параметризовані SQL-запити, транзакції
├── schemas.py        # Pydantic-моделі
├── config.py         # одиниця, межі value, поріг, ліміти
├── seed.py           # початкове заповнення з data/seed.json
├── routers/
│   ├── categories.py
│   └── records.py
├── data/
│   ├── seed.json     # 3 категорії, 8 записів
│   └── lab3.sqlite3  # створюється програмою, не додається до Git
└── README.md
```

## Запуск

```
python -m labs.lab03.database
python -m labs.lab03.seed
uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
```

Документація: http://127.0.0.1:8000/docs

Повторний запуск `seed` не змінює непорожню базу.

## Маршрути

| Метод | Маршрут | Відповідь |
|---|---|---|
| GET | `/ping` | 200 `{"status": "ok"}` |
| GET | `/student` | 200, ПІБ, група, варіант |
| GET | `/categories` | 200, список категорій |
| POST | `/categories` | 201 / 409 |
| DELETE | `/categories/{category_id}` | 204 / 404 / 409 |
| GET | `/records` | 200, параметри `category_id`, `status`, `min_value`, `q`, `limit`, `offset` |
| GET | `/records/{record_id}` | 200 / 404 |
| POST | `/records` | 201 / 404 / 409 / 422 |
| PUT | `/records/{record_id}` | 200 / 404 / 409 / 422 |
| DELETE | `/records/{record_id}` | 204 / 404 |
| POST | `/records/bulk` | 201 / 404 / 409 / 422, усі записи або жодного |

## Приклади запитів (Bash)

```
curl -i "http://127.0.0.1:8000/ping"
curl -i "http://127.0.0.1:8000/records?category_id=1&status=new&limit=5&offset=0"

curl -i -X POST "http://127.0.0.1:8000/records" \
  -H "Content-Type: application/json" \
  -d '{"code":"V03-TEST","title":"Навчальна знахідка","category_id":1,"value":7.5,"status":"new"}'

curl -i -X POST "http://127.0.0.1:8000/records/bulk" \
  -H "Content-Type: application/json" \
  -d '[{"code":"V03-ROLLBACK","title":"Перший елемент","category_id":1,"value":4.0,"status":"new"},{"code":"V03-01","title":"Дублікат коду","category_id":2,"value":5.0,"status":"new"}]'
```

Останній запит повертає `409`, запис `V03-ROLLBACK` не зберігається.

У Windows ті самі запити зручно виконувати через Swagger UI (`/docs`).

## Поведінка при помилках

- некоректні дані або параметри — `422`;
- неіснуючий запис або категорія — `404`;
- дублікат `code` чи назви категорії, видалення непорожньої категорії — `409`;
- технічна помилка бази — `500` без SQL і шляхів, деталі пишуться в лог.

## Перевірка коду

```
ruff check labs/lab03
ruff format --check labs/lab03
```
