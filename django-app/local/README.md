# Local Development with Docker Compose

This repository includes a Docker Compose setup for running the Django app and PostgreSQL database locally for testing and development.

## Quick Start

1. Create a `.env` file in the same folder as `docker-compose.local.yml` using the terraform output for the variables
   ```bash
   $env:AWS_PROFILE = 'admin-pps-wm'
   $env:AWS_REGION  = 'eu-west-2'
   $env:AWS_SDK_LOAD_CONFIG = '1'

   aws sso login --profile admin-pps-wm

   cd infra/terraform
   terraform init -reconfigure -backend-config="bucket=nhse-pps-wm-terraform-state-bucket" -backend-config="key={env}/terraform.tfstate" -backend-config="region=eu-west-2"
   terraform output -raw cognito_client_id_ci
   terraform output -raw cognito_user_pool_id
   ```

2. Build and start the containers:
   ```bash
   cd django-app
   docker build -t ppswm:local .
   docker compose -p local -f local/docker-compose.local.yml up --build -d web
   ```

3. Run DB update script
   ```bash
   docker compose -f local/docker-compose.local.yml exec web python manage.py update_db
   ```

4. Visit the app:
   - Django site → http://localhost:8000  
   - Health check → http://localhost:8000/health/
   - Public API → http://localhost:8000/public/api/ping

5. Stop containers:
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
