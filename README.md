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

При запуске Docker Compose сначала поднимает PostgreSQL, затем выполняет
`alembic upgrade head` в сервисе `migrate`, и только после успешных миграций
запускает `app`, `worker` и `bot`.

### Migrations

```bash
alembic revision --autogenerate -m "migration message"
alembic upgrade head
```

Для локального запуска Alembic без Docker используйте `DATABASE_URL` с
`localhost`. В контейнерах `DATABASE_URL` задаётся через Docker Compose и
указывает на hostname `postgres`.

Если локальный Docker volume был создан со старой схемой или другими
`POSTGRES_USER`/`POSTGRES_PASSWORD`, PostgreSQL сохранит эти старые настройки.
Такой volume нужно пересоздать один раз только если старые данные не нужны.
