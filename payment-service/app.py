"""
payment-service
Handles (mock) membership fee payments.
In-memory store only - for learning/demo purposes.
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

payments = {}
next_id = 1


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "payment-service"}), 200


@app.route("/payments", methods=["POST"])
def create_payment():
    """Record a (mock) payment for a membership."""
    global next_id
    data = request.get_json(silent=True) or {}
    membership_id = data.get("membership_id")
    amount = data.get("amount")

    if not membership_id or amount is None:
        return jsonify({"error": "membership_id and amount are required"}), 400

    payment = {
        "id": next_id,
        "membership_id": membership_id,
        "amount": amount,
        "status": "paid",
    }
    payments[next_id] = payment
    next_id += 1

    return jsonify(payment), 201


@app.route("/payments/<int:payment_id>", methods=["GET"])
def get_payment(payment_id):
    payment = payments.get(payment_id)
    if not payment:
        return jsonify({"error": "payment not found"}), 404
    return jsonify(payment), 200


@app.route("/payments", methods=["GET"])
def list_payments():
    return jsonify(list(payments.values())), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
