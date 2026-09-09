FROM python:3.12-slim

WORKDIR /app

# Устанавливаем uv для быстрой установки зависимостей
COPY --from=ghcr.io/astral-sh/uv:0.4.20 /uv /usr/local/bin/uv

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости без dev-пакетов
RUN uv sync --frozen --no-dev

# Копируем исходный код
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
