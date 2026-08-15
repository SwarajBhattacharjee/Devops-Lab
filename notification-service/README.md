# notification-service

Stores and returns mock notifications.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness check (database) |
| GET | `/metrics` | Basic request/error counters |
| POST | `/notify` | Send notification (`user_id`, `message`) |
| GET | `/notifications` | List notifications |

## Notes

- Data persists in PostgreSQL.
- Notification send validates that user exists.
