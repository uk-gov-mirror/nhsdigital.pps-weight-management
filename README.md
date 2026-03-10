<div align="center">
<br/>

# PPS Help to Stay Healthy

[![ci-main](https://github.com/NHSDigital/pps-weight-management/actions/workflows/ci-main.yml/badge.svg)](https://github.com/NHSDigital/pps-weight-management/actions/workflows/ci-main.yml)

</div>
<br>
<div align="left">

This repository contains the Help to Stay Healthy application and infrastructure code.

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
| - /                  | - /v1/                               |
|                      | - /v2/                               |
|                      | - /v3/                               |
|                      | - /admin/      # Administration Site |
|                      | - /apidocs/    # Swagger UI          |
|                      | - /health/     # Service health      |
|----------------------|--------------------------------------|
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
|                                           VPC                                               |
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
+---------------------------------------------------------------------------------------------+
```