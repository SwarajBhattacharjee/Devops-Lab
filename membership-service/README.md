# membership-service

Handles gym membership plans and sign-ups.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness check (database) |
| GET | `/metrics` | Basic request/error counters |
| GET | `/plans` | List plans |
| POST | `/signup` | Create membership (`user_id`, `plan`) |
| GET | `/memberships` | List memberships |
| GET | `/memberships/<id>` | Get membership |

## Notes

- Data persists in PostgreSQL.
- Signup validates that the target user exists.
- Duplicate active signup for same user+plan returns existing record with `duplicate: true`.
