# CareService-automation
AI consultant at Avito

## FastAPI Application

### Installation

```bash
uv sync
```

### Configuration

Copy environment variables and configure database:

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### Run

```bash
docker compose up --build
```

API будет доступен на http://127.0.0.1:8000.

Docker Compose ждёт успешной проверки готовности PostgreSQL перед запуском
`app`, `worker` и `bot`. Эти сервисы используют один набор `POSTGRES_*`
переменных; внутри Docker-сети хостом БД служит `postgres`.

### Migrations

```bash
alembic revision --autogenerate -m "migration message"
alembic upgrade head
```

Для локального запуска Alembic без Docker задайте `DATABASE_HOST=localhost`.
В Docker Compose `DATABASE_HOST` для `app`, `worker` и `bot` переопределяется
на hostname сервиса `postgres`. URL подключения собирается из `POSTGRES_*`
через SQLAlchemy `URL.create`, который корректно обрабатывает спецсимволы в
пароле.

Если локальный Docker volume был создан со старой схемой или другими
`POSTGRES_USER`/`POSTGRES_PASSWORD`, PostgreSQL сохранит эти старые настройки.
Такой volume нужно пересоздать один раз только если старые данные не нужны.
