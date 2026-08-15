import logging
import os
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, g, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

SERVICE_NAME = "membership-service"
PORT = int(os.getenv("PORT", "5002"))
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

PLANS = {
    "basic": {"name": "Basic", "price": 20, "duration_days": 30},
    "premium": {"name": "Premium", "price": 45, "duration_days": 30},
    "annual": {"name": "Annual", "price": 400, "duration_days": 365},
}


def init_db():
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS memberships (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    plan_key VARCHAR(32) NOT NULL,
                    status VARCHAR(16) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_membership_user_plan_active
                ON memberships(user_id, plan_key)
                WHERE status = 'active'
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


def serialize_membership(row):
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "plan_key": row["plan_key"],
        "plan": PLANS[row["plan_key"]],
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


@app.route("/plans", methods=["GET"])
def list_plans():
    return jsonify(PLANS), 200


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    plan_key = (data.get("plan") or "").strip().lower()

    if not isinstance(user_id, int) or plan_key not in PLANS:
        return error_response("user_id must be an integer and plan must be valid", 400)

    if not user_exists(user_id):
        return error_response("user not found", 404, "user_not_found")

    try:
        with engine.begin() as conn:
            existing = conn.execute(
                text(
                    """
                    SELECT id, user_id, plan_key, status, created_at
                    FROM memberships
                    WHERE user_id = :user_id AND plan_key = :plan_key AND status = 'active'
                    """
                ),
                {"user_id": user_id, "plan_key": plan_key},
            ).mappings().first()
            if existing:
                payload = serialize_membership(existing)
                payload["duplicate"] = True
                return jsonify(payload), 200

            created = conn.execute(
                text(
                    """
                    INSERT INTO memberships (user_id, plan_key, status)
                    VALUES (:user_id, :plan_key, 'active')
                    RETURNING id, user_id, plan_key, status, created_at
                    """
                ),
                {"user_id": user_id, "plan_key": plan_key},
            ).mappings().one()

        return jsonify(serialize_membership(created)), 201
    except SQLAlchemyError:
        logger.exception("signup_failed request_id=%s", g.request_id)
        return error_response("could not create membership", 500, "internal_error")


@app.route("/memberships/<int:membership_id>", methods=["GET"])
def get_membership(membership_id):
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, user_id, plan_key, status, created_at
                    FROM memberships
                    WHERE id = :membership_id
                    """
                ),
                {"membership_id": membership_id},
            ).mappings().first()

        if not row:
            return error_response("membership not found", 404, "not_found")
        return jsonify(serialize_membership(row)), 200
    except SQLAlchemyError:
        logger.exception("get_membership_failed request_id=%s", g.request_id)
        return error_response("could not fetch membership", 500, "internal_error")


@app.route("/memberships", methods=["GET"])
def list_memberships():
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, user_id, plan_key, status, created_at
                    FROM memberships
                    ORDER BY id
                    """
                )
            ).mappings().all()

        return jsonify([serialize_membership(row) for row in rows]), 200
    except SQLAlchemyError:
        logger.exception("list_memberships_failed request_id=%s", g.request_id)
        return error_response("could not list memberships", 500, "internal_error")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
