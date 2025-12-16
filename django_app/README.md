# Weight Management Site — Django project (Web, REST API, Scheduler, Admin)

## Project Structure
```
django_app/
  ├── api/                          # REST API
  ├── core/                         # Core fucntions
  ├── local/                        # For local testing on Docker Desktop
  ├── scheduler/                    # Scheduled task
  ├── static/                       # Static files (e.g. images)
  ├── templates/                    # Jinja2 templates
  ├── web/                          # Website
  ├── wm_django/                    # App settings
  ├── Dockerfile
  ├── manage.py
  ├── README.md
  └── requirements.txt
```
## Jinja2 Templates
Jinja2 Templates https://github.com/NHSDigital/nhsuk-frontend-jinja

## NHS UK Styling
NHS UK Frontend https://github.com/nhsuk/nhsuk-frontend

## Web Endpoints
- `/` → returns Website
- `/apidocs` → returns Swagger UI
- `/admin` → returns Admin site

## REST API Endpoints
- `/health` → returns `ok` (for ALB health checks)
- `/v1/services` → returns subset of details of services matching search criteria
- `/v1/service/{id}` → returns Full details of a sepcific service
- `/v2/services` → returns subset of details of services matching search criteria
- `/v2/service/{id}` → returns Full details of a sepcific service
- `/v3/services` → returns subset of details of services matching search criteria
- `/v3/service/{id}` → returns Full details of a sepcific service

More information: https://nhsd-confluence.digital.nhs.uk/spaces/PPP/pages/1226685095/REST+API

## Run locally in Docker Desktop
See /local
