FROM python:3.12-alpine AS test-image

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL="sqlite+aiosqlite:////app/tmp/dev.db"

WORKDIR /app

RUN apk update && apk add --no-cache make uv

COPY . .
RUN uv sync && make check

FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL="sqlite+aiosqlite:////app/tmp/prod.db"

RUN apk update && apk add --no-cache uv

WORKDIR /app

ARG UID=10000
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

COPY . .
RUN uv sync --no-dev -n

EXPOSE 5000

ENTRYPOINT ["./entrypoint.sh"]
