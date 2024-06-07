FROM python:3.10-alpine AS test-image

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP="blog"
ENV SQLALCHEMY_DATABASE_URI="sqlite:////app/tmp/dev.db"

WORKDIR /app

RUN apk update && apk add make
RUN python -m venv /app/venv


COPY . .
RUN /app/venv/bin/python3 -m pip install -r requirements.txt 
RUN /app/venv/bin/python3 -m pip install -r dev.txt


RUN source /app/venv/bin/activate && make check

FROM python:3.10-alpine AS build-image

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP="blog"
ENV SQLALCHEMY_DATABASE_URI="sqlite:////app/tmp/dev.db"

WORKDIR /app


RUN python -m venv /app/venv

COPY requirements.txt .
RUN /app/venv/bin/python3 -m pip install -r requirements.txt



FROM python:3.10-alpine
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


WORKDIR /app

#ARG UID=10001
#RUN adduser \
#    --disabled-password \
#    --gecos "" \
#    --home "/nonexistent" \
#    --shell "/sbin/nologin" \
#    --no-create-home \
#    --uid "${UID}" \
#    appuser
#USER appuser
#
COPY --from=build-image /app/venv /app/venv

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
#RUN --mount=type=cache,target=/root/.cache/pip \
#    --mount=type=bind,source=requirements.txt,target=requirements.txt \
#    pip install -r requirements.txt --break-system-packages
# Switch to the non-privileged user to run the application.
#USER appuser

# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 5000

ENV PATH=/app/venv/bin:$PATH

# Run the application.
ENTRYPOINT [ "./entrypoint.sh" ]
CMD /app/venv/bin/gunicorn -c gunicorn.py 'app:create_app()'

