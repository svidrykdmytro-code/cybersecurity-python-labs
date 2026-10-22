APP_TITLE = "Реєстр вразливостей робочих станцій"
APP_DESCRIPTION = (
    "Сервіс обліку знахідок перевірки робочих станцій (варіант 3). "
    "Категорія визначає тип програмного забезпечення (os, browser, office), "
    "value — навчальна оцінка небезпеки від 0 до 10 (одиниця: score), "
    "status — стан опрацювання знахідки. "
    "Знахідки з value не нижче порога 8.0 вважаються критичними."
)
APP_VERSION = "1.0.0"

VALUE_UNIT = "score"
VALUE_MIN = 0.0
VALUE_MAX = 10.0
THRESHOLD = 8.0

STATUSES = ("new", "in_progress", "done")

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_BULK_SIZE = 100

SEED_CATEGORIES = 3
SEED_RECORDS = 8
