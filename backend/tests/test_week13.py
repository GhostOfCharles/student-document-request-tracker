import io, json, uuid
from copy import deepcopy
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from PIL import Image
from sqlalchemy import select, func
from sqlalchemy.exc import DBAPIError
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app import models as m, schemas as s
from app.main import app
from app.db import SessionLocal, utcnow
from app.common import one, change, rows, clean
from app.automation.worker import enqueue, process, claim, finish
from app.automation.tasks import scan, generate_summary, cleanup, local_now


def config(client, pay=False):
    cards = client.get("/api/v1/services").json()["items"]
    card = next(c for c in cards if c["payment_required"] == pay)
    return client.get(f"/api/v1/services/{card['id']}").json()


def image_bytes(color="blue"):
    buffer = io.BytesIO()
    Image.new("RGB", (12, 12), color).save(buffer, format="PNG")
    return buffer.getvalue()


def upload(client, name="synthetic.png", color="blue"):
    response = client.post(
        "/api/v1/files/staging", files={"file": (name, image_bytes(color), "image/png")}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def payload(client, pay=False):
    c = config(client, pay)
    v = c["version"]
    answers = []
    attachments = []
    for field in v["requirements"]:
        kind = field["field_type"]
        fid = field["id"]
        if kind == "text":
            answers.append(
                {"requirement_id": fid, "text_value": "Synthetic scholarship purpose"}
            )
        if kind == "select":
            answers.append(
                {"requirement_id": fid, "selected_option_id": field["options"][0]["id"]}
            )
        if kind == "date":
            answers.append({"requirement_id": fid, "date_value": "2026-11-05"})
        if kind == "checkbox":
            answers.append({"requirement_id": fid, "boolean_value": True})
        if kind == "file" and field["required"]:
            attachments.append(
                {"requirement_id": fid, "stored_file_id": upload(client)}
            )
    result = {
        "client_submission_key": str(uuid.uuid4()),
        "service_id": c["id"],
        "service_version_id": v["id"],
        "answers": answers,
        "attachments": attachments,
    }
    if pay:
        result["payment"] = {
            "reference": "FICTIONAL-ONLY-001",
            "receipt_file_id": upload(client, "fictional-receipt.png", "green"),
        }
    return result


def submitted(client, pay=False):
    body = payload(client, pay)
    response = client.post("/api/v1/requests", json=body)
    assert response.status_code == 201, response.text
    return response.json(), body


def action(client, rid, name, **extras):
    detail = client.get(f"/api/v1/requests/{rid}").json()
    prefix = "" if name in {"acknowledge", "cancel"} else "/staff"
    return client.post(
        f"/api/v1{prefix}/requests/{rid}/{name}",
        json={"expected_row_version": detail["row_version"], **extras},
    )


def test_typed_inputs():
    for value in [
        {"requirement_id": 1, "text_value": "x", "boolean_value": True},
        {"requirement_id": 1, "boolean_value": "true"},
        {"requirement_id": 1, "selected_option_id": True},
    ]:
        with pytest.raises(ValidationError):
            s.Answer(**value)
    with pytest.raises(ValidationError):
        s.Login(login="x", password="x", role="staff")
    print("PASS strict types and unknown-property rejection")


def test_auth_csrf_roles_and_expiry(student, staff):
    import hashlib

    anon = TestClient(app)
    assert anon.get("/api/v1/requests").status_code == 401
    assert (
        anon.post(
            "/api/v1/auth/login", json={"login": "x", "password": "x"}
        ).status_code
        == 403
    )
    assert student.get("/api/v1/staff/automation/jobs").status_code == 403
    assert student.get("/api/v1/unknown").status_code == 404
    assert (
        student.post(
            "/api/v1/requests", json={}, headers={"origin": "https://evil.invalid"}
        ).status_code
        == 403
    )
    with SessionLocal.begin() as db:
        record = one(
            db,
            m.auth_sessions,
            m.auth_sessions.c.session_token_hash
            == hashlib.sha256(student.cookies.get("sdrt_session").encode()).digest(),
        )
        change(
            db,
            m.auth_sessions,
            record["id"],
            expires_at=utcnow() - timedelta(seconds=1),
        )
    assert student.get("/api/v1/auth/me").status_code == 401
    print("PASS sessions, expiry, origin/CSRF and roles")


def test_unpaid_lifecycle_and_replay(student, staff, other):
    created, body = submitted(student)
    rid = created["id"]
    assert other.get(f"/api/v1/requests/{rid}").status_code == 404
    assert other.post("/api/v1/requests", json=body).status_code == 404
    assert (
        action(staff, rid, "approve", confirm_requirements_valid=True).status_code
        == 409
    )
    assert action(staff, rid, "begin-review").status_code == 200
    stale = staff.post(
        f"/api/v1/staff/requests/{rid}/approve",
        json={"expected_row_version": 1, "confirm_requirements_valid": True},
    )
    assert stale.status_code == 409 and stale.json()["code"] == "VERSION_CONFLICT"
    assert (
        action(staff, rid, "approve", confirm_requirements_valid=True).status_code
        == 200
    )
    assert (
        action(staff, rid, "ready-for-release", confirm_prepared=True).status_code
        == 200
    )
    assert action(staff, rid, "release", confirm_handover=True).status_code == 200
    assert (
        action(student, rid, "acknowledge", confirm_received=True).json()["status"]
        == "completed"
    )
    replayed = student.post("/api/v1/requests", json=body)
    assert replayed.status_code == 200 and replayed.json() == created
    changed = deepcopy(body)
    changed["answers"][0]["text_value"] = "Changed purpose"
    assert (
        student.post("/api/v1/requests", json=changed).json()["code"]
        == "IDEMPOTENCY_CONFLICT"
    )
    assert student.get(f"/api/v1/requests/{rid}/history").json()["total"] == 6
    print(
        f"PASS unpaid request {rid}: complete lifecycle, version conflict, owner isolation, immutable-result replay"
    )


def test_payment_and_immutable_correction(student, staff, other):
    created, body = submitted(student, True)
    rid = created["id"]
    original = student.get(f"/api/v1/requests/{rid}/revisions/1").json()
    support = body["attachments"][0]["stored_file_id"]
    receipt = body["payment"]["receipt_file_id"]
    assert student.get(f"/api/v1/files/{support}").content == image_bytes()
    assert other.get(f"/api/v1/files/{receipt}").status_code == 404
    assert staff.get(f"/api/v1/files/{receipt}").status_code == 200
    assert student.delete(f"/api/v1/files/staging/{support}").status_code == 409
    assert action(staff, rid, "begin-review").status_code == 200
    assert (
        action(staff, rid, "approve", confirm_requirements_valid=True).json()["code"]
        == "PAYMENT_NOT_VERIFIED"
    )
    detail = student.get(f"/api/v1/requests/{rid}").json()
    assert (
        action(
            staff,
            rid,
            "payment-reviews",
            revision_id=detail["latest_revision"]["id"],
            outcome="verified",
        ).status_code
        == 201
    )
    cr = action(
        staff,
        rid,
        "corrections",
        general_instructions="Replace synthetic image.",
        items=[
            {
                "target_kind": "requirement",
                "requirement_id": body["attachments"][0]["requirement_id"],
                "instruction": "Use a clearer synthetic image.",
            }
        ],
    )
    assert cr.status_code == 201, cr.text
    detail = student.get(f"/api/v1/requests/{rid}").json()
    corrected = {
        k: v for k, v in body.items() if k not in ("service_id", "service_version_id")
    }
    corrected.update(
        client_submission_key=str(uuid.uuid4()),
        expected_row_version=detail["row_version"],
        correction_round_id=cr.json()["correction_round_id"],
    )
    corrected["attachments"] = [
        dict(
            body["attachments"][0],
            stored_file_id=upload(student, "replacement.png", "red"),
        )
    ]
    bad = deepcopy(corrected)
    bad["answers"][0]["text_value"] = "Unpermitted change"
    assert (
        student.post(
            f"/api/v1/requests/{rid}/correction-submissions", json=bad
        ).status_code
        == 422
    )
    response = student.post(
        f"/api/v1/requests/{rid}/correction-submissions", json=corrected
    )
    assert response.status_code == 201, response.text
    assert student.get(f"/api/v1/requests/{rid}/revisions/1").json() == original
    assert (
        action(staff, rid, "approve", confirm_requirements_valid=True).json()["code"]
        == "PAYMENT_NOT_VERIFIED"
    )
    detail = student.get(f"/api/v1/requests/{rid}").json()
    assert detail["latest_revision"]["payment"]["receipt_file_id"] == receipt
    assert (
        action(
            staff,
            rid,
            "payment-reviews",
            revision_id=detail["latest_revision"]["id"],
            outcome="verified",
        ).status_code
        == 201
    )
    assert (
        action(staff, rid, "approve", confirm_requirements_valid=True).status_code
        == 200
    )
    assert (
        student.post(
            f"/api/v1/requests/{rid}/correction-submissions", json=corrected
        ).json()
        == response.json()
    )
    assert student.get(f"/api/v1/requests/{rid}/revisions").json()["total"] == 2
    with pytest.raises(DBAPIError):
        with SessionLocal.begin() as db:
            db.execute(
                m.request_revisions.update()
                .where(m.request_revisions.c.id == original["id"])
                .values(payment_reference="tamper")
            )
    print(
        f"PASS paid request {rid}: immutable correction, targeted edits, secure bytes, payment re-review, DB trigger"
    )


def test_upload_validation_and_notes(student, staff, other):
    staged = upload(student)
    assert staff.get(f"/api/v1/files/{staged}").status_code == 404
    assert other.get(f"/api/v1/files/{staged}").status_code == 404
    assert (
        student.post(
            "/api/v1/files/staging",
            files={"file": ("bad.png", b"not-a-png", "image/png")},
        ).status_code
        == 415
    )
    assert (
        student.post(
            "/api/v1/files/staging",
            files={"file": ("bad.pdf", b"%PDF-corrupt", "application/pdf")},
        ).status_code
        == 422
    )
    assert (
        student.post(
            "/api/v1/files/staging",
            files={"file": ("huge.png", b"x" * 5242881, "image/png")},
        ).status_code
        == 413
    )
    body = payload(student)
    body["answers"] = []
    assert student.post("/api/v1/requests", json=body).status_code == 422
    body = payload(student)
    body["answers"].append(deepcopy(body["answers"][0]))
    assert student.post("/api/v1/requests", json=body).status_code == 422
    created, _ = submitted(student)
    rid = created["id"]
    before = student.get(f"/api/v1/requests/{rid}").json()["last_progress_at"]
    for visibility in ("staff_only", "student_visible"):
        assert (
            staff.post(
                f"/api/v1/staff/requests/{rid}/notes",
                json={"visibility": visibility, "note_body": "Synthetic note"},
            ).status_code
            == 201
        )
    assert student.get(f"/api/v1/requests/{rid}/notes").json()["total"] == 1
    assert student.get(f"/api/v1/requests/{rid}").json()["last_progress_at"] == before
    assert action(staff, rid, "begin-review").status_code == 200
    assert (
        action(staff, rid, "reject", reason="Synthetic rejection").json()["status"]
        == "rejected"
    )
    print(
        "PASS private staging, corrupt/oversize rejection, requirements, note privacy and rejection"
    )


def test_aging_summary_cleanup_and_read(student, staff):
    created, _ = submitted(student)
    rid = created["id"]
    now = utcnow()
    with SessionLocal.begin() as db:
        change(
            db,
            m.document_requests,
            rid,
            due_at=now - timedelta(hours=49),
            last_progress_at=now - timedelta(hours=73),
        )
    scan(now)
    scan(now)
    with SessionLocal() as db:
        assert (
            len(
                rows(
                    db,
                    m.request_alerts,
                    m.request_alerts.c.request_id == rid,
                    m.request_alerts.c.resolved_at.is_(None),
                )
            )
            == 2
        )
    process(now)
    notes = staff.get("/api/v1/notifications?page_size=100").json()["items"]
    nid = notes[0]["id"]
    read = staff.patch(f"/api/v1/notifications/{nid}/read").json()["read_at"]
    assert staff.patch(f"/api/v1/notifications/{nid}/read").json()["read_at"] == read
    summary = generate_summary(now)
    assert summary["pending_total"] == sum(
        summary[k + "_count"]
        for k in (
            "submitted",
            "under_review",
            "needs_correction",
            "processing",
            "ready_for_release",
            "released",
        )
    )
    assert summary["aging_count"] >= 1 and summary["escalated_count"] >= 1
    assert (
        staff.post(
            "/api/v1/staff/reports/daily/regenerate",
            json={"date": local_now(now).date().isoformat()},
        ).status_code
        == 200
    )
    assert (
        staff.post(
            "/api/v1/staff/reports/daily/regenerate", json={"date": "2000-01-01"}
        ).status_code
        == 422
    )
    assert action(staff, rid, "begin-review").status_code == 200
    detail = student.get(f"/api/v1/requests/{rid}").json()
    field = detail["latest_revision"]["answers"][0]["requirement_id"]
    assert (
        action(
            staff,
            rid,
            "corrections",
            general_instructions="Correct test purpose",
            items=[
                {
                    "target_kind": "requirement",
                    "requirement_id": field,
                    "instruction": "Correct test purpose",
                }
            ],
        ).status_code
        == 201
    )
    with SessionLocal() as db:
        assert not rows(
            db,
            m.request_alerts,
            m.request_alerts.c.request_id == rid,
            m.request_alerts.c.resolved_at.is_(None),
        )
    unused = upload(student)
    with SessionLocal.begin() as db:
        change(
            db, m.stored_files, unused, staging_expires_at=now - timedelta(seconds=1)
        )
    cleanup(now)
    assert student.get(f"/api/v1/files/{unused}").status_code == 404
    print(
        "PASS aging/escalation deduplication, correction suspension, local summary, read behavior and cleanup"
    )


def test_failure_recovery_and_manual_action(student, staff):
    created, _ = submitted(student)
    rid = created["id"]
    process()
    now = utcnow()
    with SessionLocal.begin() as db:
        uid = one(db, m.users, m.users.c.role == "staff")["id"]

        def inject(key, **flags):
            return enqueue(
                db,
                "notification",
                "experiment:" + key,
                request_id=rid,
                recipient_user_id=uid,
                payload={
                    "event_key": "experiment:" + key,
                    "title": "Controlled synthetic failure experiment",
                    **flags,
                },
                now=now,
            )

        transient = inject("transient", _test_transient=True)
        permanent = inject("permanent", _test_permanent=True)
        exhausted = inject("ceiling", _test_always_transient=True)
        interrupted = inject("interrupted")
    process(now, limit=3)
    stale = claim(now, worker="interrupted-test-worker")
    assert stale and stale["job_id"] == interrupted
    process(now + timedelta(minutes=1))
    process(now + timedelta(minutes=6))
    assert finish(stale, now + timedelta(minutes=7)) is False
    process(now + timedelta(days=1))
    with SessionLocal() as db:
        trans = one(db, m.automation_jobs, m.automation_jobs.c.id == transient)
        perm = one(db, m.automation_jobs, m.automation_jobs.c.id == permanent)
        ceil = one(db, m.automation_jobs, m.automation_jobs.c.id == exhausted)
        assert trans["status"] == "succeeded" and trans["attempt_count"] == 2
        assert perm["status"] == "failed_permanently" and perm["attempt_count"] == 1
        assert ceil["status"] == "failed_permanently" and ceil["attempt_count"] == 3
        for key in ("transient", "interrupted"):
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(m.notifications)
                    .where(
                        m.notifications.c.recipient_user_id == uid,
                        m.notifications.c.event_key == "experiment:" + key,
                    )
                )
                == 1
            )
        assert (
            one(db, m.automation_jobs, m.automation_jobs.c.id == interrupted)[
                "attempt_count"
            ]
            == 2
        )
    assert permanent in [
        j["id"]
        for j in staff.get(
            "/api/v1/staff/automation/jobs?status=failed_permanently"
        ).json()["items"]
    ]
    assert student.get(f"/api/v1/staff/automation/jobs/{permanent}").status_code == 403
    resolution = staff.post(
        f"/api/v1/staff/automation/jobs/{permanent}/resolve",
        json={
            "resolution_note": "Synthetic configuration inspected; manual registrar handling recorded without asserting delivery."
        },
    )
    assert (
        resolution.status_code == 200
        and resolution.json()["status"] == "resolved_manually"
    )
    assert (
        staff.post(
            f"/api/v1/staff/automation/jobs/{permanent}/retry",
            json={"reason": "No retry after resolution"},
        ).status_code
        == 409
    )
    assert (
        staff.post(
            f"/api/v1/staff/automation/jobs/{exhausted}/retry",
            json={"reason": "Controlled retry cycle one"},
        ).json()["max_attempts"]
        == 6
    )
    for minutes in (0, 1, 6):
        process(now + timedelta(days=2, minutes=minutes))
    assert (
        staff.post(
            f"/api/v1/staff/automation/jobs/{exhausted}/retry",
            json={"reason": "Controlled retry cycle two"},
        ).json()["max_attempts"]
        == 9
    )
    for minutes in (0, 1, 6):
        process(now + timedelta(days=3, minutes=minutes))
    assert (
        staff.post(
            f"/api/v1/staff/automation/jobs/{exhausted}/retry",
            json={"reason": "Disallowed cycle three"},
        ).status_code
        == 409
    )
    with SessionLocal() as db:
        evidence = {
            str(jid): {
                "job": {
                    k: v
                    for k, v in one(
                        db, m.automation_jobs, m.automation_jobs.c.id == jid
                    ).items()
                    if k not in ("payload_json", "locked_by")
                },
                "attempts": [
                    {k: v for k, v in a.items() if k != "worker_identifier"}
                    for a in rows(
                        db,
                        m.automation_attempts,
                        m.automation_attempts.c.automation_job_id == jid,
                        order=m.automation_attempts.c.attempt_number,
                    )
                ],
            }
            for jid in (transient, permanent, exhausted, interrupted)
        }
        assert evidence[str(exhausted)]["job"]["attempt_count"] == 9
    from app.config import ROOT

    (ROOT / "evidence/week13/activity2/observed-jobs.json").write_text(
        json.dumps(clean(evidence), indent=2)
    )
    print(
        f"PASS failure experiment: transient {transient} recovered at 2; permanent {permanent} visible then manually handled; ceiling {exhausted} stopped at 3/6/9; interrupted {interrupted} recovered, exactly one notification, stale finalizer rejected"
    )


def test_concurrent_submission_and_staff_race(student, staff):
    body = payload(student)
    with ThreadPoolExecutor(2) as pool:
        responses = list(
            pool.map(lambda _: student.post("/api/v1/requests", json=body), range(2))
        )
    assert sorted(r.status_code for r in responses) == [200, 201]
    rid = responses[0].json()["id"]
    assert responses[1].json()["id"] == rid
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda _: staff.post(
                    f"/api/v1/staff/requests/{rid}/begin-review",
                    json={"expected_row_version": 1},
                ),
                range(2),
            )
        )
    assert sorted(r.status_code for r in results) == [200, 409]
    print("PASS concurrent idempotent submission and staff row-version race")
