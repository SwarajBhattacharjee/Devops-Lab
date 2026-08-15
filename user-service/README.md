# user-service

Handles gym member registration and profile lookups.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness check (database) |
| GET | `/metrics` | Basic request/error counters |
| POST | `/users` | Register a user (`name`, `email`) |
| GET | `/users` | List users |
| GET | `/users/<id>` | Get a user |

## Notes

- Data persists in PostgreSQL.
- Duplicate email registration returns the existing user with `duplicate: true`.
