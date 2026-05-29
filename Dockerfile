FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/

RUN uv sync --no-dev

COPY data/ ./data/

ENV PYTHONPATH=/app/src

CMD ["uv", "run", "python", "-m", "portbattle_bot.main"]