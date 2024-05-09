# Dockerfile - this is a comment. Delete me if you want.
FROM python:3.12
WORKDIR /app
RUN apt update && apt install make -y
COPY  requirements.txt /app
RUN pip install -r requirements.txt
ENV SQLALCHEMY_DATABASE_URI="sqlite:////app/tmp/dev.db"
COPY . /app
ENV FLASK_APP="blog"
CMD ["make", "run"]
