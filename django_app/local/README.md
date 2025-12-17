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
   terraform init -reconfigure -backend-config="bucket=nhse-pps-wm-terraform-state-bucket" -backend-config="key=poc/terraform.tfstate" -backend-config="region=eu-west-2"
   terraform output -raw cognito_client_id_ci
   terraform output -raw cognito_user_pool_id
   ```

2. Build and start the containers:
   ```bash
   cd django_app
   # Start Docker Desktop
   docker build --target local -t ppswm:local .
   docker compose -p local -f local/docker-compose.local.yml up -d web
   docker compose -f local/docker-compose.local.yml exec web python manage.py migrate
   docker compose -f local/docker-compose.local.yml exec web python manage.py createsuperuser --noinput
   ```

3. Run DB update script to create tables and seed data
   ```bash
   docker compose -f local/docker-compose.local.yml exec web python manage.py update_db
   ```
   
   If running tests load the test data
   ```bash
   docker compose -f local/docker-compose.local.yml exec web python manage.py v3_load_testdata
   ```

4. Connect VS Code for debugging

5. Visit the app:
   - Django site → http://127.0.0.1:8000  
   - Health check → http://127.0.0.1:8000/health/
   - REST API → http://127.0.0.1:8000/apidocs
   - Admin → http://127.0.0.1:8000/admin

6. Stop containers:
   ```bash
   docker compose -p local -f local\docker-compose.local.yml stop web db
   ```

## Common Commands

| Task | Command |
|------|----------|
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
