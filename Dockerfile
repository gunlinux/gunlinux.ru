# Dockerfile - this is a comment. Delete me if you want.
FROM alpine:3.19
RUN apk update && apk add py3-pip py3-virtualenv
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP="blog"
ENV SQLALCHEMY_DATABASE_URI="sqlite:////app/tmp/dev.db"
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser


# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install -r requirements.txt --break-system-packages
# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY . .
COPY gunicorn.example.conf  gunicorn.conf 

# Expose the port that the application listens on.
EXPOSE 5000

# Run the application.
CMD gunicorn -c gunicorn.conf 'app:create_app()' --bind=0.0.0.0:5000
