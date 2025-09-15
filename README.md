# PPS Weight Management

## Status
**Under development** Currently testing and developing the no-regrets tech stack, CICD pipelines, and AWS resources needed. The website deployed is a simple "Hello World" for testing the infrastrcuture.

##Project Structure
```
.
├── .github/
│   └── workflows/                    # GitHub Actions
├── docs/                             # Documentation
├── infra/
│   └── terraform/
│       ├── bootstrap/                # Create AWS resources (run once)
│       ├── envs/                     # Environment configuration files
│       │   └── poc/                  
│       │       └── poc.tfvars        # Variables for poc environment
│       └── main.tf                   # The main Terraform configuration file
├── lambda/
│   ├── api/                          # API tests
│   │   └── src/                      # REST API source code
│   └── daily/
│       └── src/                      # Daily scheduled job source code
├── scripts/                          # Scripts
├── tests/                            # 
│   ├── api/                          # API tests
│   └── ui/                           # UI tests
├── web/                              # Static website
└── README.md                         # README file for project.
```

## Infrastructure
This repository deploys a **public static website** (S3 + CloudFront + WAF), and a **public REST API** and a **JWT-protected secure REST API** (API Gateway HTTP API + Lambda Node/TypeScript + DynamoDB) using **Terraform** and **GitHub Actions (OIDC)**. It also deploys Event Scheduler to trigger a daily scheduled job.
```
               +--------------------------+
               |    AWS WAFv2 Web ACL     |
               |   (Global Protection)    |
               +------------+-------------+
                            |
                            v
 +----------------------------------------------------------------+
 |            AWS CloudFront (CDN Distribution)                   |
 |                                                                |
 |  +------------------+ +--------------------------------------+ |
 |  |  Static Content  | |          API Requests                | |
 |  |   (path: /*)     | | (paths: /public/api/*,/secure/api/*) | |
 |  +------------------+ +--------------------------------------+ |
 |           |                            |                       |
 +----------------------------------------------------------------+
             |                            |
             v                            v
    +----------------+           +-----------------+
    |  S3 Bucket     |           |   API Gateway   |
    | (Static Site)  |           |   (HTTP API)    |
    +----------------+           +-----------------+
                                          |
                                          |
                          +---------------+-------------+
                          |  Public API   | Secure API  |
                          |  (No Auth)    | (JWT Auth)  |
                          +---------------+-------------+
                                  |       |   Cognito   |
   +------------------+           |       |  User Pool  |
   | Event Scheduler  |           |       +-------------+
   |                  |           |             |
   +--------+---------+           +-------------+
            |                             |
            v                             v
   +--------+---------+         +------------------+
   |    AWS Lambda    |         |    AWS Lambda    |
   |    (Daily Job)   |         |   (API Backend)  |
   +------------------+         +--------+---------+
                                         |
                                         v
                                +------------------+
                                |  AWS DynamoDB    |
                                | (Data Storage)   |
                                +------------------+
```
