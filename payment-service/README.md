# payment-service

Handles (mock) membership fee payments.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/payments` | Record a payment (`membership_id`, `amount`) |
| GET | `/payments` | List all payments |
| GET | `/payments/<id>` | Get a single payment |

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Runs on `http://localhost:5003`.
