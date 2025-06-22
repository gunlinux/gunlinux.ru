FROM python:3.10-alpine AS test-image

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP="blog"
ENV SQLALCHEMY_DATABASE_URI="sqlite:////app/tmp/dev.db"

WORKDIR /app

RUN apk update && apk add --no-cache nodejs npm make uv

COPY . .
RUN uv sync && make check && make test

FROM python:3.10-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP="blog"
ENV SQLALCHEMY_DATABASE_URI="sqlite:////app/tmp/dev.db"

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
#   --no-create-home \
#   appuser


# Copy the source code into the container.
COPY . .
RUN uv sync --no-dev -n
# Expose the port that the application listens on.
EXPOSE 5000

ENV PATH=/app/venv/bin:$PATH

#USER appuser

# Run the application.
ENTRYPOINT [ "./entrypoint.sh" ]
#CMD [ "uv", "run gunicorn -c gunicorn.py "]

