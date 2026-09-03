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
uvicorn src.main:app --reload
```

### Migrations

```bash
alembic revision --autogenerate -m "migration message"
alembic upgrade head
```
