# notification-service

Sends (mock) welcome/renewal notifications to gym members.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/notify` | Send a notification (`user_id`, `message`) |
| GET | `/notifications` | List all sent notifications |

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Runs on `http://localhost:5004`.
