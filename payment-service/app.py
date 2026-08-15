import logging
import os
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, g, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

SERVICE_NAME = "payment-service"
PORT = int(os.getenv("PORT", "5003"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://devops@localhost:5432/devops_lab")
MEMBERSHIP_SERVICE_URL = os.getenv("MEMBERSHIP_SERVICE_URL", "http://membership-service:5002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:5004")

app = Flask(__name__)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(SERVICE_NAME)

metrics = {"requests_total": 0, "requests_errors": 0}


def init_db():
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    membership_id INTEGER NOT NULL,
                    amount NUMERIC(10,2) NOT NULL,
                    status VARCHAR(16) NOT NULL DEFAULT 'paid',
                    idempotency_key VARCHAR(128),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_idempotency_key
                ON payments(idempotency_key)
                WHERE idempotency_key IS NOT NULL
                """
            )
        )


def now_iso(ts):
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).isoformat()
    return ts


def error_response(message, status_code, code="bad_request"):
    return (
        jsonify(
            {
                "error": {
                    "message": message,
                    "code": code,
                    "request_id": getattr(g, "request_id", None),
                }
            }
        ),
        status_code,
    )


def fetch_membership(membership_id):
    try:
        response = requests.get(f"{MEMBERSHIP_SERVICE_URL}/memberships/{membership_id}", timeout=2)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        logger.exception("membership_lookup_failed membership_id=%s", membership_id)
    return None


def send_notification(user_id, membership_id, amount):
    message = f"Payment received for membership {membership_id}: ${amount:.2f}"
    try:
        requests.post(
            f"{NOTIFICATION_SERVICE_URL}/notify",
            json={"user_id": user_id, "message": message},
            timeout=2,
        )
    except requests.RequestException:
        logger.warning("notification_send_failed user_id=%s", user_id)


def serialize_payment(row):
    return {
        "id": row["id"],
        "membership_id": row["membership_id"],
        "amount": float(row["amount"]),
        "status": row["status"],
        "idempotency_key": row["idempotency_key"],
        "created_at": now_iso(row["created_at"]),
    }


@app.before_request
def before_request():
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    metrics["requests_total"] += 1


@app.after_request
def after_request(response):
    response.headers["X-Request-ID"] = g.request_id
    if response.status_code >= 400:
        metrics["requests_errors"] += 1
    logger.info(
        "request_complete service=%s request_id=%s method=%s path=%s status=%s",
        SERVICE_NAME,
        g.request_id,
        request.method,
        request.path,
        response.status_code,
    )
    return response


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": SERVICE_NAME}), 200


@app.route("/ready", methods=["GET"])
def ready():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify({"status": "ready", "service": SERVICE_NAME}), 200
    except SQLAlchemyError:
        return error_response("database not ready", 503, "not_ready")


@app.route("/metrics", methods=["GET"])
def get_metrics():
    return jsonify({"service": SERVICE_NAME, **metrics}), 200


@app.route("/payments", methods=["POST"])
def create_payment():
    data = request.get_json(silent=True) or {}
    membership_id = data.get("membership_id")
    amount = data.get("amount")
    idempotency_key = (
        request.headers.get("X-Idempotency-Key") or data.get("idempotency_key") or None
    )

    if not isinstance(membership_id, int):
        return error_response("membership_id must be an integer", 400)

    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        return error_response("amount must be a valid number", 400)

    if amount_value <= 0:
        return error_response("amount must be greater than zero", 400)

    membership = fetch_membership(membership_id)
    if not membership:
        return error_response("membership not found", 404, "membership_not_found")

    try:
        with engine.begin() as conn:
            if idempotency_key:
                existing = conn.execute(
                    text(
                        """
                        SELECT id, membership_id, amount, status, idempotency_key, created_at
                        FROM payments
                        WHERE idempotency_key = :idempotency_key
                        """
                    ),
                    {"idempotency_key": idempotency_key},
                ).mappings().first()
                if existing:
                    payload = serialize_payment(existing)
                    payload["idempotent_replay"] = True
                    return jsonify(payload), 200

            created = conn.execute(
                text(
                    """
                    INSERT INTO payments (membership_id, amount, status, idempotency_key)
                    VALUES (:membership_id, :amount, 'paid', :idempotency_key)
                    RETURNING id, membership_id, amount, status, idempotency_key, created_at
                    """
                ),
                {
                    "membership_id": membership_id,
                    "amount": amount_value,
                    "idempotency_key": idempotency_key,
                },
            ).mappings().one()

        user_id = membership.get("user_id")
        if isinstance(user_id, int):
            send_notification(user_id, membership_id, amount_value)

        return jsonify(serialize_payment(created)), 201
    except SQLAlchemyError:
        logger.exception("create_payment_failed request_id=%s", g.request_id)
        return error_response("could not create payment", 500, "internal_error")


@app.route("/payments/<int:payment_id>", methods=["GET"])
def get_payment(payment_id):
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, membership_id, amount, status, idempotency_key, created_at
                    FROM payments
                    WHERE id = :payment_id
                    """
                ),
                {"payment_id": payment_id},
            ).mappings().first()

        if not row:
            return error_response("payment not found", 404, "not_found")
        return jsonify(serialize_payment(row)), 200
    except SQLAlchemyError:
        logger.exception("get_payment_failed request_id=%s", g.request_id)
        return error_response("could not fetch payment", 500, "internal_error")


@app.route("/payments", methods=["GET"])
def list_payments():
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, membership_id, amount, status, idempotency_key, created_at
                    FROM payments
                    ORDER BY id
                    """
                )
            ).mappings().all()

        return jsonify([serialize_payment(row) for row in rows]), 200
    except SQLAlchemyError:
        logger.exception("list_payments_failed request_id=%s", g.request_id)
        return error_response("could not list payments", 500, "internal_error")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
