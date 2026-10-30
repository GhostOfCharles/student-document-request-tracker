"""Read-only live API smoke evidence; uses controlled account, never logs cookies."""

import json, sys
from pathlib import Path
from datetime import datetime, timezone
import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
config = dotenv_values(ROOT / ".env")
events = []


def checked(name, response, status=200):
    assert response.status_code == status, (name, response.status_code, response.text)
    events.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "check": name,
            "http_status": response.status_code,
            "result": "PASS",
        }
    )
    return response.json() if response.content else None


with httpx.Client(
    base_url="http://localhost:8000", headers={"Origin": "http://localhost:8000"}
) as c:
    token = checked("CSRF binding", c.get("/api/v1/auth/csrf"))["csrf_token"]
    checked(
        "real MySQL student login",
        c.post(
            "/api/v1/auth/login",
            json={
                "login": "student@example.test",
                "password": config["SDRT_SEED_PASSWORD"],
            },
            headers={"X-CSRF-Token": token},
        ),
    )
    services = checked("two published MySQL services", c.get("/api/v1/services"))
    assert services["total"] == 2 and {
        s["payment_required"] for s in services["items"]
    } == {True, False}
    checked("role-aware dashboard", c.get("/api/v1/dashboard"))
    checked(
        "student denied staff automation", c.get("/api/v1/staff/automation/jobs"), 403
    )
    checked("unknown API stays 404", c.get("/api/v1/nonexistent"), 404)
    token = checked("renew CSRF after login", c.get("/api/v1/auth/csrf"))["csrf_token"]
    checked(
        "session revoked on logout",
        c.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token}),
        204,
    )
    checked("revoked session denied", c.get("/api/v1/auth/me"), 401)
output = ROOT / "evidence/week13/verification/api-smoke.json"
output.write_text(json.dumps(events, indent=2), encoding="utf-8")
print(
    json.dumps(
        {"result": "PASS", "checks": len(events), "evidence": str(output)}, indent=2
    )
)
