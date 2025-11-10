# helloworld — Django project (web, api, core, scheduler, templates)

## Apps & responsibilities
- **core**: health endpoint and utilities
- **web**: Jinja2 server-rendered pages (Hello World)
- **api**: REST endpoints (`/public/api/*` public, `/secure/api/*` protected by ALB+Cognito)
- **scheduler**: background jobs; includes `daily_job.py`
- **templates**: shared templates (plus app-specific templates under `templates/web/...`)

## Endpoints
- `/` → Hello World page (Jinja2)
- `/health` → returns `ok` (for ALB health checks)
- `/public/api/ping` → returns `pong`
- `/secure/api/items` → GET list, POST create
- `/secure/api/items/<id>` → GET one

> `/secure/api/*` should be protected at the **ALB** using a Cognito authentication rule, but we have no domain or certificate so cannot implement https which is needed. As a temp workaround token parsing is implemented in Django.

## Run locally
```
python -m venv .venv
source .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Run locally in Docker Desktop
See /local
