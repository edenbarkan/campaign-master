FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY tests ./tests
COPY entrypoint.sh /entrypoint.sh

ENV FLASK_APP=app

CMD ["/entrypoint.sh"]
