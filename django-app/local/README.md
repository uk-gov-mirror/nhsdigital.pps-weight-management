# Local Development with Docker Compose

This repository includes a Docker Compose setup for running the Django app and PostgreSQL database locally for testing and development.

## Quick Start

1. Create a `.env` file in the same folder as `docker-compose.local.yml`:
   ```env
   POSTGRES_DB=app
   POSTGRES_USER=app
   POSTGRES_PASSWORD=app
   POSTGRES_HOST=db
   POSTGRES_PORT=5432
   DJANGO_DEBUG=True
   DJANGO_SECRET_KEY=local-secret-key
   ```

2. Build and start the containers:
   ```bash
   docker build -t ppswm:local .
   docker compose -p local -f local/docker-compose.local.yml up --build -d web
   ```

3. Visit the app:
   - Django site → http://localhost:8000  
   - Health check → http://localhost:8000/health/
   - Public API → http://localhost:8000/public/api/ping

4. Stop containers:
   ```bash
   docker compose -p local -f local\docker-compose.local.yml stop web db
   ```

## Common Commands

| Task | Command |
|------|----------|
| Rebuild after changes | `docker compose build web && docker compose up -d` |
| View all logs | `docker compose -f local/docker-compose.local.yml logs -f` |
| View web logs | `docker compose -f local/docker-compose.local.yml logs -f web` |
| View DB logs | `docker compose -f local/docker-compose.local.yml logs -f db` |
| Run DB update script | `docker compose -f local/docker-compose.local.yml exec web python manage.py update_db` |

## Database Access

To open a PostgreSQL shell inside the container:
```bash
docker compose -f local/docker-compose.local.yml exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

Useful psql commands:
```sql
\dt                -- List tables
SELECT * FROM my_table LIMIT 10;
\q                 -- Quit
```
