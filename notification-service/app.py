"""
notification-service
Sends (mock) welcome/renewal notifications to members.
No real email/SMS is sent - this just logs and returns the "sent" notification.
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

notifications = []


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "notification-service"}), 200


@app.route("/notify", methods=["POST"])
def notify():
    """Send a (mock) notification."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    message = data.get("message")

    if not user_id or not message:
        return jsonify({"error": "user_id and message are required"}), 400

    notification = {
        "user_id": user_id,
        "message": message,
        "status": "sent",
    }
    notifications.append(notification)

    return jsonify(notification), 201


@app.route("/notifications", methods=["GET"])
def list_notifications():
    return jsonify(notifications), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004, debug=True)
