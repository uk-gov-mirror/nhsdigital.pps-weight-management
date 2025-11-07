# helloworld — structured Django project (web, api, core, scheduler, templates)

## Apps & responsibilities
- **core**: health endpoint and cross-cutting utilities
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

> Protect `/secure/api/*` at the **ALB** using a Cognito authentication rule. No token parsing is required in Django.

## Run locally
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Docker
Build & run:
```
docker build -t helloworld:dev .
docker run --rm -p 8000:8000 helloworld:dev
```
ECS web service uses the image CMD (Gunicorn). The scheduled task should override command to:
```
python manage.py daily_job
```

## Settings
- Default dev run: `helloworld.settings.dev` (via manage.py)
- Container default: `helloworld.settings.prod`
Set `DJANGO_SETTINGS_MODULE` in ECS task definition if you need to override.
