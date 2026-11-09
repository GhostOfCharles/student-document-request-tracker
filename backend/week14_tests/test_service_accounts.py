"""Week 14 checks against a dedicated disposable MySQL schema."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

assert os.environ.get("SDRT_ENVIRONMENT") == "test"
assert make_url(os.environ["SDRT_DATABASE_URL"]).database.endswith("_test")

from app import models as m
from app.auth import hasher
from app.common import add, change, one
from app.db import SessionLocal
from app.main import app
from app.automation.worker import process
from sqlalchemy import func, select

PASSWORD = "DevelopmentPass-14!"
ORIGIN = "http://localhost:8000"


@pytest.fixture(autouse=True)
def independent_rate_limits():
    from app.auth import login_limits, registration_limits
    login_limits.clear()
    registration_limits.clear()


@pytest.fixture(scope="module")
def accounts():
    token = uuid.uuid4().hex[:10]
    with SessionLocal.begin() as db:
        accounts = {}
        for name, role, manager in [
            ("manager", "staff", True), ("clerk", "staff", False), ("student", "student", False)
        ]:
            email = f"w14-{name}-{token}@example.test"
            uid = add(db, m.users, role=role, email=email, full_name="Week 14 " + name,
                      student_number=f"W14-{token}" if role == "student" else None,
                      staff_number=f"W14-{name}-{token}" if role == "staff" else None,
                      password_hash=hasher.hash(PASSWORD), can_manage_services=manager,
                      is_active=True, must_change_password=False)
            accounts[name] = {"email": email, "id": uid}
        return accounts


def client_for(email, password=PASSWORD):
    client = TestClient(app)
    client.headers["origin"] = ORIGIN
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    login = client.post("/api/v1/auth/login", json={"login": email, "password": password})
    assert login.status_code == 200, login.text
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    return client


def config():
    return {
        "name": "Example Enrollment", "description": "Unverified example",
        "category": "Example", "eligibility_instructions": "Confirm requirements with registrar.",
        "processing_days": 3,
        "payment": {"required": False, "amount": None, "currency": "PHP",
                    "instructions": None, "reference_required": False, "receipt_required": False},
        "requirements": [
            {"field_key": "purpose", "label": "Purpose", "field_type": "text",
             "required": True, "max_length": 200, "options": []},
            {"field_key": "term", "label": "Term", "field_type": "select", "required": True,
             "options": [{"value": "first", "label": "First semester"},
                         {"value": "second", "label": "Second semester"}]},
        ],
    }


def test_registration_profile_password_and_session_revocation(accounts):
    token = uuid.uuid4().hex[:10]
    client = TestClient(app)
    client.headers["origin"] = ORIGIN
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    body = {"full_name": "Test Student", "student_number": "REG-" + token,
            "email": f"registered-{token}@example.test", "password": PASSWORD,
            "password_confirmation": PASSWORD, "terms_accepted": True}
    result = client.post("/api/v1/auth/register", json=body)
    assert result.status_code == 201, result.text
    assert result.json()["role"] == "student" and result.json()["can_manage_services"] is False
    assert client.post("/api/v1/auth/register", json=body).status_code == 409
    body["student_number"] += "x"
    body["password_confirmation"] = "different-password"
    assert client.post("/api/v1/auth/register", json=body).status_code == 422
    logged = client_for(result.json()["email"])
    profile = logged.patch("/api/v1/account/me", json={"phone_number": "000000000"})
    assert profile.status_code == 200
    assert profile.json()["phone_number"] == "000000000"
    assert logged.patch("/api/v1/account/me", json={"role": "staff"}).status_code == 422
    assert logged.post("/api/v1/account/password", json={
        "current_password": "incorrect", "new_password": "NewDevelopmentPass-14!",
        "new_password_confirmation": "NewDevelopmentPass-14!",
    }).status_code == 401
    changed = logged.post("/api/v1/account/password", json={
        "current_password": PASSWORD, "new_password": "NewDevelopmentPass-14!",
        "new_password_confirmation": "NewDevelopmentPass-14!",
    })
    assert changed.status_code == 204
    assert logged.get("/api/v1/auth/me").status_code == 401
    assert client_for(result.json()["email"], "NewDevelopmentPass-14!").get("/api/v1/auth/me").status_code == 200


def test_service_manager_versions_and_request_pinning(accounts):
    manager = client_for(accounts["manager"]["email"])
    clerk = client_for(accounts["clerk"]["email"])
    student = client_for(accounts["student"]["email"])
    code = "W14_" + uuid.uuid4().hex[:12].upper()
    body = {"service_code": code, "configuration": config()}
    assert student.post("/api/v1/staff/services", json=body).status_code == 403
    assert clerk.post("/api/v1/staff/services", json=body).status_code == 403
    created = manager.post("/api/v1/staff/services", json=body)
    assert created.status_code == 201, created.text
    draft = created.json()
    sid = draft["id"]
    version = draft["version"]
    assert draft["is_active"] is False
    assert any(item["id"] == sid for item in manager.get(
        "/api/v1/staff/services", params={"q": "Example Enrollment", "availability": "inactive"}
    ).json()["items"])
    assert all(item["id"] != sid for item in clerk.get(
        "/api/v1/staff/services", params={"q": "Example Enrollment"}
    ).json()["items"])
    assert clerk.get(f"/api/v1/staff/services/{sid}/draft").status_code == 403
    assert student.get(f"/api/v1/services/{sid}").status_code == 404
    published = manager.post(f"/api/v1/staff/services/{sid}/publish",
                             json={"expected_row_version": version["row_version"], "activate": True})
    assert published.status_code == 200, published.text
    published_v1 = published.json()["version"]
    process()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(m.notifications).where(
            m.notifications.c.recipient_user_id == accounts["student"]["id"],
            m.notifications.c.service_id == sid,
            m.notifications.c.event_key == f"service_published:{sid}:{published_v1['id']}",
        )) == 1
    assert student.get(f"/api/v1/services/{sid}").json()["version"]["id"] == published_v1["id"]
    reqs = published_v1["requirements"]
    submission = {"client_submission_key": str(uuid.uuid4()), "service_id": sid,
                  "service_version_id": published_v1["id"], "attachments": [],
                  "answers": [
                      {"requirement_id": reqs[0]["id"], "text_value": "Scholarship"},
                      {"requirement_id": reqs[1]["id"], "selected_option_id": reqs[1]["options"][0]["id"]},
                  ]}
    request = student.post("/api/v1/requests", json=submission)
    assert request.status_code == 201, request.text
    new_draft = manager.post(f"/api/v1/staff/services/{sid}/draft")
    assert new_draft.status_code == 201, new_draft.text
    dv = new_draft.json()["version"]
    assert dv["version_number"] == 2 and dv["requirements"][0]["id"] != reqs[0]["id"]
    # Convert server output to the documented editable configuration.
    updated = {k: dv[k] for k in ("name", "description", "category", "eligibility_instructions", "processing_days", "payment")}
    updated["requirements"] = [{k: f[k] for k in ("id", "field_key", "label", "help_text", "field_type",
        "required", "min_length", "max_length", "allowed_mime_types", "max_file_size_bytes", "options")}
        for f in dv["requirements"]]
    updated["requirements"][0]["label"] = "Reason for request"
    assert manager.put(f"/api/v1/staff/services/{sid}/draft",
                       json={"expected_row_version": 999, "configuration": updated}).status_code == 409
    saved = manager.put(f"/api/v1/staff/services/{sid}/draft",
                        json={"expected_row_version": dv["row_version"], "configuration": updated})
    assert saved.status_code == 200, saved.text
    assert manager.post(f"/api/v1/staff/services/{sid}/publish",
        json={"expected_row_version": saved.json()["version"]["row_version"], "activate": True}).status_code == 200
    current = student.get(f"/api/v1/services/{sid}").json()["version"]
    assert current["version_number"] == 2 and current["requirements"][0]["label"] == "Reason for request"
    old = student.get(f"/api/v1/requests/{request.json()['id']}").json()
    assert old["service"]["version"]["id"] == published_v1["id"]
    assert old["service"]["version"]["requirements"][0]["label"] == "Purpose"
    assert student.post("/api/v1/requests", json=submission).status_code == 200
    assert manager.patch(f"/api/v1/staff/services/{sid}/availability",
        json={"is_active": False, "expected_current_version_id": published_v1["id"]}).status_code == 409
    assert manager.patch(f"/api/v1/staff/services/{sid}/availability",
        json={"is_active": False, "expected_current_version_id": current["id"]}).status_code == 200
    assert student.get(f"/api/v1/services/{sid}").status_code == 404
    assert student.get(f"/api/v1/requests/{request.json()['id']}").status_code == 200
    assert manager.patch(f"/api/v1/staff/services/{sid}/availability",
        json={"is_active": True, "expected_current_version_id": current["id"]}).status_code == 200
    assert manager.patch(f"/api/v1/staff/services/{sid}/availability",
        json={"is_active": False, "expected_current_version_id": current["id"]}).status_code == 200
    assert manager.patch(f"/api/v1/staff/services/{sid}/availability",
        json={"is_active": True, "expected_current_version_id": current["id"]}).status_code == 200
    process()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(m.notifications).where(
            m.notifications.c.recipient_user_id == accounts["student"]["id"],
            m.notifications.c.service_id == sid,
            m.notifications.c.event_key == f"service_published:{sid}:{current['id']}",
        )) == 1
    history = clerk.get(f"/api/v1/staff/services/{sid}").json()["published_versions"]
    assert len(history) == 2


def test_configuration_rejects_invalid_payment_and_file_rules(accounts):
    manager = client_for(accounts["manager"]["email"])
    bad = config()
    bad["payment"] = {"required": True, "amount": "50.00", "currency": "PHP",
                      "instructions": "", "reference_required": False, "receipt_required": False}
    assert manager.post("/api/v1/staff/services",
        json={"service_code": "BAD_" + uuid.uuid4().hex[:8].upper(), "configuration": bad}).status_code == 422
    bad = config()
    bad["requirements"] = [{"field_key": "evidence", "label": "Evidence", "field_type": "file",
        "required": True, "allowed_mime_types": ["application/zip"], "max_file_size_bytes": 5242880}]
    assert manager.post("/api/v1/staff/services",
        json={"service_code": "BAD_" + uuid.uuid4().hex[:8].upper(), "configuration": bad}).status_code == 422


def test_password_whitespace_is_preserved():
    token = uuid.uuid4().hex[:10]
    client = TestClient(app)
    client.headers["origin"] = ORIGIN
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    password = "  space-sensitive-14!  "
    email = f"space-{token}@example.test"
    result = client.post("/api/v1/auth/register", json={
        "full_name": "  Test Student  ", "student_number": "SPACE-" + token,
        "email": email, "password": password, "password_confirmation": password,
        "terms_accepted": True,
    })
    assert result.status_code == 201, result.text
    assert result.json()["full_name"] == "Test Student"
    assert client_for(email, password).get("/api/v1/auth/me").status_code == 200
    denied = client.post("/api/v1/auth/login", json={"login": email, "password": password.strip()})
    assert denied.status_code == 401


def test_temporary_staff_password_must_be_changed():
    token = uuid.uuid4().hex[:10]
    email = f"temporary-{token}@example.test"
    with SessionLocal.begin() as db:
        add(db, m.users, role="staff", email=email, full_name="Temporary staff",
            student_number=None, staff_number="TEMP-" + token, password_hash=hasher.hash(PASSWORD),
            can_manage_services=False, is_active=True, must_change_password=True)
    client = client_for(email)
    assert client.get("/api/v1/auth/me").json()["must_change_password"] is True
    assert client.get("/api/v1/dashboard").status_code == 403
    assert client.patch("/api/v1/account/me", json={"phone_number": "000"}).status_code == 403
    result = client.post("/api/v1/account/password", json={
        "current_password": PASSWORD, "new_password": "NewDevelopmentPass-14!",
        "new_password_confirmation": "NewDevelopmentPass-14!",
    })
    assert result.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    updated = client_for(email, "NewDevelopmentPass-14!")
    assert updated.get("/api/v1/auth/me").json()["must_change_password"] is False
    assert updated.get("/api/v1/dashboard").status_code == 200


def test_student_cancellation_respects_workflow_states(accounts):
    manager = client_for(accounts["manager"]["email"])
    student = client_for(accounts["student"]["email"])
    body = {"service_code": "CANCEL_" + uuid.uuid4().hex[:10].upper(), "configuration": config()}
    created = manager.post("/api/v1/staff/services", json=body).json()
    sid = created["id"]
    version = manager.post(f"/api/v1/staff/services/{sid}/publish", json={
        "expected_row_version": created["version"]["row_version"], "activate": True,
    }).json()["version"]
    fields = version["requirements"]

    def submit():
        response = student.post("/api/v1/requests", json={
            "client_submission_key": str(uuid.uuid4()), "service_id": sid,
            "service_version_id": version["id"], "attachments": [],
            "answers": [
                {"requirement_id": fields[0]["id"], "text_value": "Test purpose"},
                {"requirement_id": fields[1]["id"], "selected_option_id": fields[1]["options"][0]["id"]},
            ],
        })
        assert response.status_code == 201, response.text
        return response.json()

    first = submit()
    cancelled = student.post(f"/api/v1/requests/{first['id']}/cancel",
                             json={"expected_row_version": first["row_version"], "reason": "Test cancellation"})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    second = submit()
    review = manager.post(f"/api/v1/staff/requests/{second['id']}/begin-review",
                          json={"expected_row_version": second["row_version"]}).json()
    cancelled = student.post(f"/api/v1/requests/{second['id']}/cancel",
                             json={"expected_row_version": review["row_version"], "reason": "Test cancellation"})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    third = submit()
    review = manager.post(f"/api/v1/staff/requests/{third['id']}/begin-review",
                          json={"expected_row_version": third["row_version"]}).json()
    correction = manager.post(f"/api/v1/staff/requests/{third['id']}/corrections", json={
        "expected_row_version": review["row_version"], "general_instructions": "Correct the purpose.",
        "items": [{"target_kind": "requirement", "requirement_id": fields[0]["id"], "instruction": "Correct it."}],
    })
    assert correction.status_code == 201, correction.text
    assert student.post(f"/api/v1/requests/{third['id']}/cancel", json={
        "expected_row_version": correction.json()["row_version"], "reason": "Test cancellation",
    }).status_code == 409
