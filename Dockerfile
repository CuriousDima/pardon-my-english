FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

COPY telegram-bot/ /app/telegram-bot/
COPY common/ /app/common/

# TELEGRAM_BOT_TOKEN and OPENROUTER_API_KEY must be provided at runtime, e.g. `docker run -e ...`.
ENV DB_URI="sqlite:////app/data/pardon-my-english-accounts.db"
ENV PATH="/app/.venv/bin:${PATH}"

VOLUME /app/data
RUN mkdir -p /app/data

CMD ["python", "telegram-bot/bot.py"]
