import logging
import os
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, g, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

SERVICE_NAME = "notification-service"
PORT = int(os.getenv("PORT", "5004"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://devops@localhost:5432/devops_lab")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5001")

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
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    status VARCHAR(16) NOT NULL DEFAULT 'sent',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
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


def user_exists(user_id):
    try:
        response = requests.get(f"{USER_SERVICE_URL}/users/{user_id}", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        logger.exception("user_lookup_failed user_id=%s", user_id)
        return False


def serialize_notification(row):
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "message": row["message"],
        "status": row["status"],
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


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    message = (data.get("message") or "").strip()

    if not isinstance(user_id, int) or not message:
        return error_response("user_id must be an integer and message is required", 400)

    if not user_exists(user_id):
        return error_response("user not found", 404, "user_not_found")

    try:
        with engine.begin() as conn:
            created = conn.execute(
                text(
                    """
                    INSERT INTO notifications (user_id, message, status)
                    VALUES (:user_id, :message, 'sent')
                    RETURNING id, user_id, message, status, created_at
                    """
                ),
                {"user_id": user_id, "message": message},
            ).mappings().one()

        return jsonify(serialize_notification(created)), 201
    except SQLAlchemyError:
        logger.exception("notify_failed request_id=%s", g.request_id)
        return error_response("could not send notification", 500, "internal_error")


@app.route("/notifications", methods=["GET"])
def list_notifications():
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, user_id, message, status, created_at
                    FROM notifications
                    ORDER BY id
                    """
                )
            ).mappings().all()

        return jsonify([serialize_notification(row) for row in rows]), 200
    except SQLAlchemyError:
        logger.exception("list_notifications_failed request_id=%s", g.request_id)
        return error_response("could not list notifications", 500, "internal_error")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
