FROM python:3.12-slim

WORKDIR /app

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:0.4.20 /uv /usr/local/bin/uv

# Зависимости
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

# Исходники
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Скрипт запуска
COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN chmod +x /docker-entrypoint.sh

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/docker-entrypoint.sh"]