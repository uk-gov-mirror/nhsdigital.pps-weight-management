# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=helloworld.settings.prod

RUN adduser --disabled-password --gecos "" appuser
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir gunicorn

COPY . .

USER appuser
EXPOSE 8000

CMD ["gunicorn", "helloworld.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
