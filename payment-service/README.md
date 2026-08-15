# payment-service

Handles mock membership fee payments.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness check (database) |
| GET | `/metrics` | Basic request/error counters |
| POST | `/payments` | Create payment (`membership_id`, `amount`) |
| GET | `/payments` | List payments |
| GET | `/payments/<id>` | Get payment |

## Notes

- Data persists in PostgreSQL.
- Payment validates that the target membership exists.
- `X-Idempotency-Key` enables idempotent payment creation.
