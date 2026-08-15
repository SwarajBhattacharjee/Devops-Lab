import json
import sys
import time
import urllib.error
import urllib.request

BASE = {
    "user": "http://localhost:5001",
    "membership": "http://localhost:5002",
    "payment": "http://localhost:5003",
    "notification": "http://localhost:5004",
}


def request_json(method, url, payload=None, headers=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def wait_ready(url, retries=30):
    for _ in range(retries):
        try:
            status, _ = request_json("GET", f"{url}/ready")
            if status == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(f"service not ready: {url}")


def main():
    for service_url in BASE.values():
        wait_ready(service_url)

    status, user = request_json("POST", f"{BASE['user']}/users", {"name": "Sam", "email": "sam@example.com"})
    assert status == 201, f"user create failed: {status}, {user}"

    status, membership = request_json(
        "POST",
        f"{BASE['membership']}/signup",
        {"user_id": user["id"], "plan": "basic"},
    )
    assert status == 201, f"membership signup failed: {status}, {membership}"

    status, payment = request_json(
        "POST",
        f"{BASE['payment']}/payments",
        {"membership_id": membership["id"], "amount": 20},
        headers={"X-Idempotency-Key": "payment-1"},
    )
    assert status == 201, f"payment create failed: {status}, {payment}"

    status, replay = request_json(
        "POST",
        f"{BASE['payment']}/payments",
        {"membership_id": membership["id"], "amount": 20},
        headers={"X-Idempotency-Key": "payment-1"},
    )
    assert status == 200 and replay.get("idempotent_replay") is True, (
        f"idempotency failed: {status}, {replay}"
    )

    status, notifications = request_json("GET", f"{BASE['notification']}/notifications")
    assert status == 200 and len(notifications) >= 1, "notification flow failed"

    print("Smoke test passed")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, RuntimeError, urllib.error.URLError) as exc:
        print(f"Smoke test failed: {exc}")
        sys.exit(1)
