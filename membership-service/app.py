"""
membership-service
Handles membership plans and member sign-ups.
In-memory store only - for learning/demo purposes.
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

# Predefined membership plans
PLANS = {
    "basic": {"name": "Basic", "price": 20, "duration_days": 30},
    "premium": {"name": "Premium", "price": 45, "duration_days": 30},
    "annual": {"name": "Annual", "price": 400, "duration_days": 365},
}

# In-memory sign-ups: membership_id -> record
memberships = {}
next_id = 1


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "membership-service"}), 200


@app.route("/plans", methods=["GET"])
def list_plans():
    return jsonify(PLANS), 200


@app.route("/signup", methods=["POST"])
def signup():
    """Sign a user up for a membership plan."""
    global next_id
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    plan_key = data.get("plan")

    if not user_id or plan_key not in PLANS:
        return jsonify({"error": "user_id and a valid plan are required"}), 400

    record = {
        "id": next_id,
        "user_id": user_id,
        "plan": PLANS[plan_key],
        "status": "active",
    }
    memberships[next_id] = record
    next_id += 1

    return jsonify(record), 201


@app.route("/memberships/<int:membership_id>", methods=["GET"])
def get_membership(membership_id):
    record = memberships.get(membership_id)
    if not record:
        return jsonify({"error": "membership not found"}), 404
    return jsonify(record), 200


@app.route("/memberships", methods=["GET"])
def list_memberships():
    return jsonify(list(memberships.values())), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
