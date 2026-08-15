# user-service

Handles gym member registration and profile lookups.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/users` | Register a new member (`name`, `email`) |
| GET | `/users` | List all members |
| GET | `/users/<id>` | Get a single member |

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Runs on `http://localhost:5001`.
