FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.6.6 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

COPY telegram-bot/ /app/telegram-bot/
COPY common/ /app/common/

ENV DB_URI="sqlite:////app/data/pardon-my-english-accounts.db"
ENV PATH="/app/.venv/bin:${PATH}"
ENV TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

VOLUME /app/data
RUN mkdir /app/data

CMD ["uv", "run", "python", "telegram-bot/bot.py"]
