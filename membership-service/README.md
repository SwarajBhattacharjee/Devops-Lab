# membership-service

Handles gym membership plans and sign-ups.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/plans` | List available membership plans |
| POST | `/signup` | Sign a user up (`user_id`, `plan`) |
| GET | `/memberships` | List all sign-ups |
| GET | `/memberships/<id>` | Get a single sign-up |

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Runs on `http://localhost:5002`.
