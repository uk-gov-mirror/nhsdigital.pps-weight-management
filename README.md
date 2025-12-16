# PPS Weight Management

##Project Structure
```
.
├── .github/
│   └── workflows/                    # GitHub Actions
├── django_app/                       # Django app
├── docs/                             # Documentation
├── infra/
│   └── terraform/
│       ├── bootstrap/                # Create AWS resources (run once)
│       ├── envs/                     # Environment configuration files
│       │   └── poc/                  
│       │       └── poc.tfvars        # Variables for poc environment
│       └── main.tf                   # The main Terraform configuration file
├── scripts/                          # Scripts
├── tests/                            # 
│   ├── api/                          # API tests
│   └── ui/                           # UI tests
└── README.md                         # README file for project.
```

## Infrastructure
```
                    +-------------------------------------+
                    |           (Public Internet)         |
                    +--------------------+----------------+
                                         |
                                         v
+-----------------------+       only CloudFront        +-----------------------+
|  AWS WAF (CLOUDFRONT) | <==========================> |  Amazon CloudFront    |
|  Web ACL: site_waf    |                              |  (distribution)*      |
+-----------+-----------+                              +-----------+-----------+
            | (filters)                                             |
            |                                                       v
            |                                        +-------------------------------+
            |  allows only CloudFront prefix list    |  Application Load Balancer    |
            +--------------------------------------> |  (ALB) in PUBLIC subnets      |
                                                     |  SG: alb                      |
                                                     +-------+-----------------------+
                                                             |
                                              HTTP:80 -> TG  | forwards to target group
                                                             v
+---------------------------------------------------------------------------------------------+
|                                  VPC (from module.vpc)                                      |
|                                                                                             |
|  Subnets:                                                                                   |
|    - PUBLIC  : ALB                                                                          |
|    - PRIVATE : ECS tasks, RDS                                                               |
|                                                                                             |
|   +-----------------------------------+                  +--------------------------------+ |
|   |  ECS Cluster: app                 |                  |  RDS: PostgreSQL (pg)          | |
|   |  Service: web (FARGATE)           |                  |  DB Subnet Group: private      | |
|   |  TaskDef: django (container 'web')|                  |  SG: db                        | |
|   |  SG: svc                          |                  |  Not publicly accessible       | |
|   |  - Receives from ALB target group |                  |  - Allows ingress from SG svc  | |
|   |  - No public IP (awsvpc)          |                  +--------------------------------+ |
|   |                                   |                                                     |
|   +---------------------+-------------+                                                     |
|                         |                                                                   |
|                         | uses image from                                                   |
|                         v                                                                   |
|              +------------------------+                                                     |
|              | Amazon ECR: django repo |  <-- Images pushed by CI via IAM OIDC role         |
|              +------------------------+                                                     |
|                                                                                             |
|   Scheduled jobs (private subnets, no public IP):                                           |
|   +-----------------------------------+                                                     |
|   |  EventBridge Scheduler (daily)    | --> runs --> Fargate TaskDef: cron (container 'job')|
|   |  IAM role: scheduler_run_ecs      |       in ECS Cluster: app, SG: svc                  |
|   +-----------------------------------+                                                     |
+---------------------------------------------------------------------------------------------+
```

## Django application
```
+-------------------------------------------------------------+
|                     Django Application                      |
|-------------------------------------------------------------|
|   Runs inside ECS Fargate (Gunicorn + Django)               |
|   Serves both HTML web views and REST API endpoints         |
+----------------------+--------------------------------------+
|      Web Frontend    |      REST API                        |
|----------------------|--------------------------------------|
| - /                  | - /public/api/                       |
|                      | - /secure/api/  (Requires JWT auth)  |
|                      | - /health/                           |
|----------------------|--------------------------------------|
```
