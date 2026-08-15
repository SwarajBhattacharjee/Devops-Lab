import logging
import os
import re
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

SERVICE_NAME = "user-service"
PORT = int(os.getenv("PORT", "5001"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://devops@localhost:5432/devops_lab")

app = Flask(__name__)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(SERVICE_NAME)

metrics = {"requests_total": 0, "requests_errors": 0}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def init_db():
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
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


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not name or not email:
        return error_response("name and email are required", 400)
    if not EMAIL_RE.match(email):
        return error_response("email format is invalid", 400)

    try:
        with engine.begin() as conn:
            existing = conn.execute(
                text("SELECT id, name, email, created_at FROM users WHERE email = :email"),
                {"email": email},
            ).mappings().first()
            if existing:
                return (
                    jsonify(
                        {
                            "id": existing["id"],
                            "name": existing["name"],
                            "email": existing["email"],
                            "created_at": now_iso(existing["created_at"]),
                            "duplicate": True,
                        }
                    ),
                    200,
                )

            created = conn.execute(
                text(
                    """
                    INSERT INTO users (name, email)
                    VALUES (:name, :email)
                    RETURNING id, name, email, created_at
                    """
                ),
                {"name": name, "email": email},
            ).mappings().one()

        return (
            jsonify(
                {
                    "id": created["id"],
                    "name": created["name"],
                    "email": created["email"],
                    "created_at": now_iso(created["created_at"]),
                }
            ),
            201,
        )
    except SQLAlchemyError:
        logger.exception("create_user_failed request_id=%s", g.request_id)
        return error_response("could not create user", 500, "internal_error")


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    try:
        with engine.connect() as conn:
            user = conn.execute(
                text("SELECT id, name, email, created_at FROM users WHERE id = :id"),
                {"id": user_id},
            ).mappings().first()

        if not user:
            return error_response("user not found", 404, "not_found")

        return (
            jsonify(
                {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "created_at": now_iso(user["created_at"]),
                }
            ),
            200,
        )
    except SQLAlchemyError:
        logger.exception("get_user_failed request_id=%s", g.request_id)
        return error_response("could not fetch user", 500, "internal_error")


@app.route("/users", methods=["GET"])
def list_users():
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, name, email, created_at FROM users ORDER BY id")
            ).mappings().all()

        users = [
            {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "created_at": now_iso(row["created_at"]),
            }
            for row in rows
        ]
        return jsonify(users), 200
    except SQLAlchemyError:
        logger.exception("list_users_failed request_id=%s", g.request_id)
        return error_response("could not list users", 500, "internal_error")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
