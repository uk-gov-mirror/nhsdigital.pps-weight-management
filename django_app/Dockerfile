# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12

# ---- Stage 1: build CSS ----
FROM node:22-alpine AS assets
WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install
COPY . .
RUN npm run build-css

# ---- Stage 2: build Django app ----
FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

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
COPY --from=assets /app/static/assets/css ./static/assets/css

# Shared runtime stage: same static behavior everywhere
FROM base AS runtime
RUN python manage.py collectstatic --noinput && rm -rf static/assets/sass

# LOCAL: (Docker Desktop debugging)
FROM runtime AS local
ENV DJANGO_SETTINGS_MODULE=wm_django.settings.dev
RUN pip install --no-cache-dir debugpy
EXPOSE 8000 5678
CMD ["python","-X","frozen_modules=off","-m","debugpy","--listen","0.0.0.0:5678","manage.py","runserver","0.0.0.0:8000","--noreload"]

# DEV: (cloud dev environment, no debugging hooks)
FROM runtime AS dev
ENV DJANGO_SETTINGS_MODULE=wm_django.settings.dev
EXPOSE 8000
CMD ["gunicorn","wm_django.wsgi:application","--bind","0.0.0.0:8000","--workers","2"]

# 3) PROD (cloud prod environment)
FROM runtime AS prod
ENV DJANGO_SETTINGS_MODULE=wm_django.settings.prod
EXPOSE 8000
CMD ["gunicorn","wm_django.wsgi:application","--bind","0.0.0.0:8000","--workers","3"]