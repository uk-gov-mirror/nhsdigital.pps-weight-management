# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12 \
    INSTALL_CA_CERTS=false

# ---- Stage 1: build CSS ----
FROM node:22-alpine AS assets
WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install
COPY . .
RUN npm run build-css

# ---- Stage 2: build Django app ----
FROM python:${PYTHON_VERSION}-slim AS base

# Conditional logic to copy certs if they are needed (ie using a corporate proxy). This feels a bit hacky so something to revisit later.
COPY certs/*.crt /usr/local/share/ca-certificates/
ARG INSTALL_CA_CERTS
RUN if [ "$INSTALL_CA_CERTS" = "true" ] && [ -d "/usr/local/share/ca-certificates/" ]; then \
    chmod 644 /usr/local/share/ca-certificates/*.crt && \
    update-ca-certificates && \
    pip install --no-cache-dir certifi && \
    ln -sf /etc/ssl/certs/ca-certificates.crt $(python -m certifi); \
    else \
    echo "Skipping CA certificates installation"; \
    fi

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    PYTHONDONTWRITEBYTECODE=1 \
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
ENV DJANGO_SETTINGS_MODULE=config.settings.dev
RUN pip install --no-cache-dir debugpy
EXPOSE 8000 5678
CMD ["python","-X","frozen_modules=off","-m","debugpy","--listen","0.0.0.0:5678","manage.py","runserver","0.0.0.0:8000","--noreload"]

# DEV: (cloud dev environment, no debugging hooks)
FROM runtime AS dev
ENV DJANGO_SETTINGS_MODULE=config.settings.dev
EXPOSE 8000
CMD ["gunicorn","config.wsgi:application","--bind","0.0.0.0:8000","--workers","2"]

# 3) PROD (cloud prod environment)
FROM runtime AS prod
ENV DJANGO_SETTINGS_MODULE=config.settings.prod
EXPOSE 8000
CMD ["gunicorn","config.wsgi:application","--bind","0.0.0.0:8000","--workers","3"]