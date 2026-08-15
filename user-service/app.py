"""
user-service
Handles gym member registration and profile info.
In-memory store only - for learning/demo purposes.
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory "database"
users = {}
next_id = 1


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "user-service"}), 200


@app.route("/users", methods=["POST"])
def create_user():
    """Register a new gym member."""
    global next_id
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    email = data.get("email")

    if not name or not email:
        return jsonify({"error": "name and email are required"}), 400

    user = {"id": next_id, "name": name, "email": email}
    users[next_id] = user
    next_id += 1

    return jsonify(user), 201


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = users.get(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user), 200


@app.route("/users", methods=["GET"])
def list_users():
    return jsonify(list(users.values())), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
