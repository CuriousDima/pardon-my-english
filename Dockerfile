FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies first so they're cached independently of code changes.
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md /app/
COPY src/ /app/src/
RUN uv sync --frozen --no-dev

# TELEGRAM_BOT_TOKEN and OPENROUTER_API_KEY must be provided at runtime, e.g. `docker run -e ...`.
ENV DB_URI="sqlite:////app/data/pardon-my-english-accounts.db"
ENV PATH="/app/.venv/bin:${PATH}"

RUN mkdir -p /app/data
VOLUME /app/data

CMD ["pardon-my-english"]
