# Devops Lab

A small microservices playground built to practice **DevOps workflows** (Git branching, staging/committing, merging, and pushing to GitHub) using a fictional **gym membership system** as the sample application.

The "business" behind this project: a gym where people sign up for memberships, manage their profile, pay membership fees, and get notified about their membership status.

## Why this exists

This repo is for learning/practicing:
- Git fundamentals: init, add, commit
- Branching strategies (Git-flow: `main` → `develop` → `feature/*`)
- Merging branches
- Pushing a multi-service repo to GitHub

It is **not** a production system — the services are intentionally minimal Flask apps with in-memory data.

## Microservices

| Service | Responsibility | Port |
|---|---|---|
| `user-service` | Register/login gym members, store profile info | 5001 |
| `membership-service` | Create/manage membership plans & sign-ups | 5002 |
| `payment-service` | Handle (mock) membership fee payments | 5003 |
| `notification-service` | Send (mock) welcome/renewal notifications | 5004 |

## Project structure

```
devops-lab/
├── README.md
├── .gitignore
├── docker-compose.yml
├── user-service/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── membership-service/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── payment-service/
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
└── notification-service/
    ├── app.py
    ├── requirements.txt
    ├── Dockerfile
    └── README.md
```

## Running a service locally

```bash
cd user-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Running everything with Docker Compose

```bash
docker-compose up --build
```

## Branching model used in this repo

- `main` — always stable/deployable
- `develop` — integration branch, features get merged here first
- `feature/<service-name>` — one branch per microservice while it's being built

See the accompanying step-by-step Git guide for exact commands.
