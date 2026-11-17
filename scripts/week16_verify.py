"""Week 16 isolated staging verification suite.

Exercises the full Nginx -> Flutter Web release bundle + FastAPI -> MySQL 8.4 (sdrt_staging)
+ APScheduler + Private Storage stack at http://localhost:8080 and captures reproducible
exit evidence under evidence/week16/.
"""

import hashlib
import html
import io
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values
from PIL import Image
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

CFG = dotenv_values(ROOT / ".env")
STAGING_URL = make_url(CFG["SDRT_DATABASE_URL"]).set(database="sdrt_staging")
STAGING_PRIVATE = ROOT / ".private/staging_uploads"
BACKUP_ROOT = ROOT / ".local/staging-backups"

os.environ["SDRT_DATABASE_URL"] = STAGING_URL.render_as_string(hide_password=False)
os.environ["SDRT_PRIVATE_DIR"] = str(STAGING_PRIVATE)
os.environ["SDRT_ENVIRONMENT"] = "staging"

from app import models as m  # noqa: E402
from app.automation.worker import enqueue  # noqa: E402
from app.db import utcnow  # noqa: E402

BASE = "http://localhost:8080"
PASSWORD = CFG["SDRT_SEED_PASSWORD"]
PYTHON = str(ROOT / "backend/.venv/Scripts/python.exe")
MYSQL_BIN = Path(r"C:\laragon\bin\mysql\mysql-8.4.3-winx64\bin")
MYSQL_EXE = str(MYSQL_BIN / "mysql.exe")
MYSQLDUMP_EXE = str(MYSQL_BIN / "mysqldump.exe")

EVIDENCE = ROOT / "evidence/week16"
LOGS = EVIDENCE / "logs"
VERIFY = EVIDENCE / "verification"
SHOTS = EVIDENCE / "screenshots"
for d in (LOGS, VERIFY, SHOTS, BACKUP_ROOT, STAGING_PRIVATE):
    d.mkdir(parents=True, exist_ok=True)

engine = create_engine(os.environ["SDRT_DATABASE_URL"], pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def png_bytes(color="navy", size=(160, 120)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def login_client(login_id: str) -> tuple[httpx.Client, str]:
    c = httpx.Client(base_url=BASE, headers={"Origin": BASE}, timeout=15.0)
    csrf = c.get("/api/v1/auth/csrf").json()["csrf_token"]
    r = c.post(
        "/api/v1/auth/login",
        json={"login": login_id, "password": PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200, (login_id, r.status_code, r.text)
    time.sleep(0.1)
    assert c.get("/api/v1/auth/me").status_code == 200
    csrf2 = c.get("/api/v1/auth/csrf").json()["csrf_token"]
    c.headers["X-CSRF-Token"] = csrf2
    return c, csrf2


def build_submission(client: httpx.Client, pay: bool) -> tuple[dict, dict]:
    services = client.get("/api/v1/services").json()["items"]
    card = next(item for item in services if item["payment_required"] == pay)
    detail = client.get(f"/api/v1/services/{card['id']}").json()
    version = detail["version"]
    answers = []
    attachments = []
    uploaded_meta = {}
    for field in version["requirements"]:
        kind = field["field_type"]
        fid = field["id"]
        if kind == "text":
            answers.append(
                {
                    "requirement_id": fid,
                    "text_value": "Week 16 staging verification request",
                }
            )
        elif kind == "select":
            answers.append(
                {"requirement_id": fid, "selected_option_id": field["options"][0]["id"]}
            )
        elif kind == "date":
            answers.append({"requirement_id": fid, "date_value": "2026-11-20"})
        elif kind == "checkbox":
            answers.append({"requirement_id": fid, "boolean_value": True})
        elif kind == "file" and field["required"]:
            raw = png_bytes("teal")
            up = client.post(
                "/api/v1/files/staging",
                files={"file": ("supporting-doc.png", raw, "image/png")},
            )
            assert up.status_code == 201, up.text
            fjson = up.json()
            uploaded_meta["supporting"] = {"id": fjson["id"], "sha256": sha256_bytes(raw)}
            attachments.append({"requirement_id": fid, "stored_file_id": fjson["id"]})

    body = {
        "client_submission_key": str(uuid.uuid4()),
        "service_id": detail["id"],
        "service_version_id": version["id"],
        "answers": answers,
        "attachments": attachments,
    }
    if pay:
        raw_r = png_bytes("darkgreen")
        up_r = client.post(
            "/api/v1/files/staging",
            files={"file": ("fictional-receipt.png", raw_r, "image/png")},
        )
        assert up_r.status_code == 201, up_r.text
        rjson = up_r.json()
        uploaded_meta["receipt"] = {"id": rjson["id"], "sha256": sha256_bytes(raw_r)}
        body["payment"] = {
            "reference": "STAGING-OR-2026-001",
            "receipt_file_id": rjson["id"],
        }
    return body, uploaded_meta


def run_smoke_tests() -> dict:
    checks = []

    def rec(name: str, resp: httpx.Response, expected: int):
        assert resp.status_code == expected, (name, resp.status_code, resp.text)
        checks.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "check": name,
                "method": resp.request.method,
                "path": resp.request.url.path,
                "http_status": resp.status_code,
                "result": "PASS",
            }
        )
        return resp

    with httpx.Client(base_url=BASE, timeout=15.0) as anon:
        r_root = rec("nginx_serves_flutter_root", anon.get("/"), 200)
        assert "X-Content-Type-Options" in r_root.headers
        assert r_root.headers.get("X-Frame-Options") == "SAMEORIGIN"
        r_spa = rec("nginx_spa_fallback_route", anon.get("/services"), 200)
        assert "<!DOCTYPE html>" in r_spa.text or "<html" in r_spa.text.lower()
        rec("nginx_blocks_hidden_dotfile", anon.get("/.env"), 404)
        r_404 = rec(
            "unknown_api_stays_json_404", anon.get("/api/v1/nonexistent"), 404
        )
        assert r_404.json()["detail"] == "API route not found."

    student, _ = login_client("TEST-001")
    staff, _ = login_client("registrar@example.test")
    try:
        rec("student_dashboard", student.get("/api/v1/dashboard"), 200)
        svc = rec("published_services_list", student.get("/api/v1/services"), 200).json()
        assert svc["total"] >= 2

        rec(
            "student_denied_staff_automation",
            student.get("/api/v1/staff/automation/jobs"),
            403,
        )

        # Submit paid request -> full staff review -> payment verify -> approve -> ready -> release -> acknowledge
        sub_body, uploaded = build_submission(student, pay=True)
        sub_res = rec(
            "student_submit_paid_request",
            student.post("/api/v1/requests", json=sub_body),
            201,
        ).json()
        rid1 = sub_res["id"]

        d = staff.get(f"/api/v1/requests/{rid1}").json()
        rev_id = d["latest_revision"]["id"]
        rv = d["row_version"]

        d = rec(
            "staff_begin_review",
            staff.post(
                f"/api/v1/staff/requests/{rid1}/begin-review",
                json={"expected_row_version": rv},
            ),
            200,
        ).json()
        d = rec(
            "staff_verify_payment",
            staff.post(
                f"/api/v1/staff/requests/{rid1}/payment-reviews",
                json={
                    "expected_row_version": d["row_version"],
                    "revision_id": rev_id,
                    "outcome": "verified",
                    "review_note": "Staging payment verified",
                },
            ),
            201,
        ).json()
        d = rec(
            "staff_approve_request",
            staff.post(
                f"/api/v1/staff/requests/{rid1}/approve",
                json={
                    "expected_row_version": d["row_version"],
                    "confirm_requirements_valid": True,
                },
            ),
            200,
        ).json()
        d = rec(
            "staff_ready_for_release",
            staff.post(
                f"/api/v1/staff/requests/{rid1}/ready-for-release",
                json={
                    "expected_row_version": d["row_version"],
                    "confirm_prepared": True,
                },
            ),
            200,
        ).json()
        d = rec(
            "staff_release_request",
            staff.post(
                f"/api/v1/staff/requests/{rid1}/release",
                json={
                    "expected_row_version": d["row_version"],
                    "confirm_handover": True,
                },
            ),
            200,
        ).json()
        rec(
            "student_acknowledge_completion",
            student.post(
                f"/api/v1/requests/{rid1}/acknowledge",
                json={
                    "expected_row_version": d["row_version"],
                    "confirm_received": True,
                },
            ),
            200,
        )

        # Submit a second request (no payment) with optional file attachment for restore verification
        sub_body2, uploaded2 = build_submission(student, pay=False)
        # Attach a non-required supporting file so request 2 also exercises private storage restore
        raw2 = png_bytes("royalblue", (240, 140))
        up2 = rec(
            "student_stage_file_for_req2",
            student.post(
                "/api/v1/files/staging",
                files={"file": ("good-moral-endorsement.png", raw2, "image/png")},
            ),
            201,
        ).json()
        # find file requirement
        svc2 = student.get(f"/api/v1/services/{sub_body2['service_id']}").json()
        file_req = next(
            r for r in svc2["version"]["requirements"] if r["field_type"] == "file"
        )
        sub_body2["attachments"].append(
            {"requirement_id": file_req["id"], "stored_file_id": up2["id"]}
        )
        sub_res2 = rec(
            "student_submit_second_request",
            student.post("/api/v1/requests", json=sub_body2),
            201,
        ).json()

        rec("student_notifications_list", student.get("/api/v1/notifications"), 200)
        rec("staff_automation_runs_list", staff.get("/api/v1/staff/automation/runs"), 200)

        # Logout and verify revoked session
        csrf_out = student.get("/api/v1/auth/csrf").json()["csrf_token"]
        rec(
            "student_logout",
            student.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_out}),
            204,
        )
        rec("revoked_session_denied", student.get("/api/v1/auth/me"), 401)
    finally:
        student.close()
        staff.close()

    report = {
        "environment": "staging (Nginx 1.30.4 on :8080 -> FastAPI :8081 -> MySQL 8.4.3 sdrt_staging)",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "result": "PASS",
        "total_checks": len(checks),
        "checks": checks,
        "seeded_requests": [sub_res["request_number"], sub_res2["request_number"]],
        "protected_file": {
            "file_id": up2["id"],
            "sha256": sha256_bytes(raw2),
            "request_number": sub_res2["request_number"],
        },
    }
    (VERIFY / "api-smoke-test-env.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def run_protected_download_tests(file_id: int, expected_sha: str) -> dict:
    results = []
    with httpx.Client(base_url=BASE, timeout=15.0) as anon:
        r401 = anon.get(f"/api/v1/files/{file_id}")
        assert r401.status_code == 401, (r401.status_code, r401.text)
        results.append(
            {
                "case": "unauthenticated_download",
                "endpoint": f"/api/v1/files/{file_id}",
                "http_status": r401.status_code,
                "code": r401.json()["code"],
                "result": "PASS",
            }
        )

    other, _ = login_client("TEST-002")
    try:
        r_other = other.get(f"/api/v1/files/{file_id}")
        assert r_other.status_code == 404, (r_other.status_code, r_other.text)
        results.append(
            {
                "case": "cross_student_isolation",
                "actor": "TEST-002",
                "endpoint": f"/api/v1/files/{file_id}",
                "http_status": r_other.status_code,
                "code": r_other.json()["code"],
                "result": "PASS",
            }
        )
    finally:
        other.close()

    owner, _ = login_client("TEST-001")
    try:
        r200 = owner.get(f"/api/v1/files/{file_id}?disposition=inline")
        assert r200.status_code == 200, (r200.status_code, r200.text)
        assert sha256_bytes(r200.content) == expected_sha
        assert r200.headers.get("Cache-Control") == "private, no-store"
        assert "sandbox" in r200.headers.get("Content-Security-Policy", "")
        results.append(
            {
                "case": "owner_authorized_download",
                "actor": "TEST-001",
                "endpoint": f"/api/v1/files/{file_id}?disposition=inline",
                "http_status": r200.status_code,
                "cache_control": r200.headers.get("Cache-Control"),
                "csp": r200.headers.get("Content-Security-Policy"),
                "sha256_verified": True,
                "result": "PASS",
            }
        )
    finally:
        owner.close()

    staff, _ = login_client("registrar@example.test")
    try:
        r_staff = staff.get(f"/api/v1/files/{file_id}")
        assert r_staff.status_code == 200, (r_staff.status_code, r_staff.text)
        assert sha256_bytes(r_staff.content) == expected_sha
        results.append(
            {
                "case": "staff_authorized_download",
                "actor": "registrar@example.test",
                "endpoint": f"/api/v1/files/{file_id}",
                "http_status": r_staff.status_code,
                "sha256_verified": True,
                "result": "PASS",
            }
        )
    finally:
        staff.close()

    # Browser verification & screenshots for 401 and 200 + Staging Nginx UI
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        # 1. Unauthenticated browser request -> 401 screenshot
        ctx_anon = browser.new_context(viewport={"width": 1280, "height": 720})
        page_anon = ctx_anon.new_page()
        resp_401 = page_anon.goto(f"{BASE}/api/v1/files/{file_id}?disposition=inline")
        assert resp_401 is not None and resp_401.status == 401
        page_anon.screenshot(path=str(SHOTS / "protected-download-401.png"))
        ctx_anon.close()

        # 2. Authenticated browser session -> Staging Flutter Web UI + 200 protected download
        ctx_auth = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx_auth.new_page()
        console_errors = []
        page.on(
            "pageerror",
            lambda err: console_errors.append(str(err)),
        )
        page.goto(BASE)
        page.wait_for_selector("flt-semantics-placeholder", state="attached")
        page.locator("flt-semantics-placeholder").evaluate("e => e.click()")
        fields = page.get_by_role("textbox")
        fields.nth(0).click()
        fields.nth(0).press_sequentially("TEST-001")
        fields.nth(1).click()
        fields.nth(1).press_sequentially(PASSWORD)
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.get_by_role("button", name="Services", exact=True)).to_be_visible(
            timeout=15000
        )
        time.sleep(1.0)
        page.screenshot(path=str(SHOTS / "staging-app-nginx.png"))
        assert not console_errors, console_errors

        dl_page = ctx_auth.new_page()
        resp_200 = dl_page.goto(f"{BASE}/api/v1/files/{file_id}?disposition=inline")
        assert resp_200 is not None and resp_200.status == 200
        dl_page.screenshot(path=str(SHOTS / "protected-download-200.png"))
        ctx_auth.close()
        browser.close()

    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "file_id": file_id,
        "sha256": expected_sha,
        "result": "PASS",
        "cases": results,
    }
    (VERIFY / "protected-download-check.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def run_scheduler_restart_test() -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")
    env["PYTHONUNBUFFERED"] = "1"

    log_lines = [
        f"=== Week 16 Scheduler Restart & Lease Recovery Test ({datetime.now(timezone.utc).isoformat()}) ==="
    ]

    # 1. Start designated scheduler #1
    proc1 = subprocess.Popen(
        [PYTHON, "-m", "app.automation.scheduler"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    started = False
    deadline = time.time() + 20
    while time.time() < deadline:
        line = proc1.stdout.readline()
        if line:
            log_lines.append(f"[scheduler-1 pid={proc1.pid}] {line.rstrip()}")
            if "scheduler_started" in line:
                started = True
                break
        elif proc1.poll() is not None:
            break
    assert started, "\n".join(log_lines)

    # 2. Verify duplicate scheduler instance is blocked by MySQL GET_LOCK
    dup = subprocess.run(
        [PYTHON, "-m", "app.automation.scheduler"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert dup.returncode != 0
    log_lines.append(
        f"[duplicate-guard exit={dup.returncode}] {(dup.stderr or dup.stdout).strip()}"
    )

    # 3. Simulate an in-flight automation run + leased job right when worker crashes
    now = utcnow()
    stale = now - timedelta(seconds=180)
    with SessionLocal.begin() as db:
        student_row = db.execute(
            select(m.users).where(m.users.c.email == "student@example.test")
        ).mappings().first()
        req_row = db.execute(
            select(m.document_requests).order_by(m.document_requests.c.id.desc())
        ).mappings().first()
        interrupted_run_id = db.execute(
            m.automation_runs.insert().values(
                job_name="aging_escalation",
                trigger_type="scheduled",
                status="running",
                started_at=stale,
                records_scanned=0,
                tasks_created=0,
            )
        ).inserted_primary_key[0]
        leased_job_id = enqueue(
            db,
            "notification",
            f"week16-restart-lease-test:{uuid.uuid4().hex[:8]}",
            request_id=req_row["id"],
            recipient_user_id=student_row["id"],
            payload={
                "notification_type": "request_status",
                "event_key": f"week16-lease-recovery:{uuid.uuid4().hex[:8]}",
                "title": "Week 16 lease recovery verification",
            },
            now=stale,
        )
        db.execute(
            m.automation_jobs.update()
            .where(m.automation_jobs.c.id == leased_job_id)
            .values(
                status="running",
                attempt_count=1,
                locked_by=f"crashed-worker:{proc1.pid}",
                locked_until=now - timedelta(seconds=30),
                updated_at=stale,
            )
        )
        db.execute(
            m.automation_attempts.insert().values(
                automation_job_id=leased_job_id,
                attempt_number=1,
                worker_identifier=f"crashed-worker:{proc1.pid}",
                started_at=stale,
                outcome="running",
            )
        )

    # 4. Abruptly kill scheduler #1 (simulating unexpected host/process crash)
    proc1.kill()
    proc1.wait(timeout=10)
    log_lines.append(
        f"[fault-injection] Killed scheduler-1 (pid={proc1.pid}, returncode={proc1.returncode}); "
        f"simulated interrupted_run_id={interrupted_run_id}, leased_job_id={leased_job_id}"
    )

    # 5. Restart designated scheduler #2 -> verify recover() + retry completion
    proc2 = subprocess.Popen(
        [PYTHON, "-m", "app.automation.scheduler"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    started2 = False
    deadline2 = time.time() + 25
    try:
        while time.time() < deadline2:
            line = proc2.stdout.readline()
            if line:
                log_lines.append(f"[scheduler-2 pid={proc2.pid}] {line.rstrip()}")
                if "scheduler_started" in line:
                    started2 = True
                    break
            elif proc2.poll() is not None:
                break
        assert started2, "\n".join(log_lines)

        with SessionLocal() as db:
            run_after = db.execute(
                select(m.automation_runs).where(
                    m.automation_runs.c.id == interrupted_run_id
                )
            ).mappings().first()
            job_after = db.execute(
                select(m.automation_jobs).where(m.automation_jobs.c.id == leased_job_id)
            ).mappings().first()
            attempts_after = db.execute(
                select(m.automation_attempts)
                .where(m.automation_attempts.c.automation_job_id == leased_job_id)
                .order_by(m.automation_attempts.c.attempt_number)
            ).mappings().all()
            notif_count = db.execute(
                select(m.notifications).where(
                    m.notifications.c.automation_job_id == leased_job_id
                )
            ).mappings().all()

        assert run_after["status"] == "failed" and run_after["error_code"] == "WORKER_INTERRUPTED"
        assert job_after["status"] == "succeeded" and job_after["attempt_count"] == 2
        assert attempts_after[0]["outcome"] == "interrupted"
        assert attempts_after[1]["outcome"] == "succeeded"
        assert len(notif_count) == 1
        log_lines.append(
            f"[verified] run={interrupted_run_id} status={run_after['status']}({run_after['error_code']}); "
            f"job={leased_job_id} status={job_after['status']} attempts={[a['outcome'] for a in attempts_after]} "
            f"notifications_created={len(notif_count)}"
        )

        # Capture Staff Automation UI screenshot while scheduler #2 is healthy
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            ctx = browser.new_context(viewport={"width": 1440, "height": 950})
            page = ctx.new_page()
            page.goto(BASE)
            page.wait_for_selector("flt-semantics-placeholder", state="attached")
            page.locator("flt-semantics-placeholder").evaluate("e => e.click()")
            fields = page.get_by_role("textbox")
            fields.nth(0).click()
            fields.nth(0).press_sequentially("registrar@example.test")
            fields.nth(1).click()
            fields.nth(1).press_sequentially(PASSWORD)
            page.get_by_role("button", name="Sign in", exact=True).click()
            expect(
                page.get_by_role("button", name="Automation", exact=True)
            ).to_be_visible(timeout=15000)
            page.get_by_role("button", name="Automation", exact=True).click()
            time.sleep(1.5)
            page.screenshot(path=str(SHOTS / "scheduler-restart-recovery.png"), full_page=True)
            ctx.close()
            browser.close()
    finally:
        proc2.terminate()
        try:
            proc2.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc2.kill()
            proc2.wait(timeout=5)
        log_lines.append(f"[shutdown] Stopped scheduler-2 cleanly (returncode={proc2.returncode})")

    (LOGS / "scheduler-restart.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return {
        "interrupted_run_id": interrupted_run_id,
        "recovered_job_id": leased_job_id,
        "attempt_outcomes": [a["outcome"] for a in attempts_after],
        "duplicate_notifications": len(notif_count) != 1,
        "result": "PASS",
    }


def run_backup_and_restore_rehearsal() -> dict:
    db_user = STAGING_URL.username
    db_pass = STAGING_URL.password or ""
    db_host = STAGING_URL.host or "127.0.0.1"
    db_port = str(STAGING_URL.port or 3306)
    db_name = STAGING_URL.database

    mysql_env = os.environ.copy()
    mysql_env["MYSQL_PWD"] = db_pass

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bdir = BACKUP_ROOT / stamp
    bdir.mkdir(parents=True, exist_ok=True)
    dump_file = bdir / f"db_{db_name}.sql"
    uploads_zip = bdir / "private_uploads.zip"

    log_lines = [
        f"=== Week 16 Paired Backup & Restore Rehearsal ({datetime.now(timezone.utc).isoformat()}) ==="
    ]

    # 1. Pre-backup inventory
    with SessionLocal() as db:
        pre_requests = db.execute(
            select(
                m.document_requests.c.id,
                m.document_requests.c.request_number,
                m.document_requests.c.status,
            ).order_by(m.document_requests.c.id)
        ).mappings().all()
        pre_files = db.execute(
            select(
                m.stored_files.c.id,
                m.stored_files.c.storage_key,
                m.stored_files.c.sha256_hex,
                m.stored_files.c.storage_status,
            ).order_by(m.stored_files.c.id)
        ).mappings().all()
        pre_triggers = [
            r[0] for r in db.execute(text("SHOW TRIGGERS")).all()
        ]
    log_lines.append(
        f"[pre-backup] requests={[r['request_number'] for r in pre_requests]} "
        f"stored_files={len(pre_files)} triggers={len(pre_triggers)}"
    )

    # 2. Execute paired backup (mysqldump + private uploads archive)
    t_bak_start = time.perf_counter()
    dump_res = subprocess.run(
        [
            MYSQLDUMP_EXE,
            f"--host={db_host}",
            f"--port={db_port}",
            f"--user={db_user}",
            "--single-transaction",
            "--routines",
            "--triggers",
            "--hex-blob",
            f"--result-file={dump_file}",
            db_name,
        ],
        env=mysql_env,
        capture_output=True,
        text=True,
        check=True,
    )
    with zipfile.ZipFile(uploads_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(STAGING_PRIVATE.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(STAGING_PRIVATE))
    bak_sec = round(time.perf_counter() - t_bak_start, 3)

    dump_sha = sha256_file(dump_file)
    zip_sha = sha256_file(uploads_zip)
    log_lines.append(
        f"$ mysqldump --single-transaction --routines --triggers --hex-blob {db_name} > db_{db_name}.sql\n"
        f"[backup-complete] duration_s={bak_sec} dump_bytes={dump_file.stat().st_size} dump_sha256={dump_sha[:16]}... "
        f"uploads_zip_bytes={uploads_zip.stat().st_size} uploads_zip_sha256={zip_sha[:16]}..."
    )

    # 3. Simulate destructive data loss (drop all staging tables + wipe private uploads)
    log_lines.append("[disaster-simulation] Dropping all tables in sdrt_staging and wiping .private/staging_uploads...")
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for tbl in inspect(engine).get_table_names():
            conn.execute(text(f"DROP TABLE IF EXISTS `{tbl}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    for item in list(STAGING_PRIVATE.iterdir()):
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    post_wipe_tables = inspect(engine).get_table_names()
    post_wipe_files = list(STAGING_PRIVATE.rglob("*"))
    assert len(post_wipe_tables) == 0 and len(post_wipe_files) == 0
    log_lines.append(
        f"[disaster-verified] tables_remaining={len(post_wipe_tables)} private_files_remaining={len(post_wipe_files)}"
    )

    # 4. Execute paired restore (verify archive checksums -> mysql restore -> extract uploads -> verify hashes & triggers)
    t_res_start = time.perf_counter()
    assert sha256_file(dump_file) == dump_sha
    assert sha256_file(uploads_zip) == zip_sha
    with dump_file.open("rb") as f_in:
        subprocess.run(
            [
                MYSQL_EXE,
                f"--host={db_host}",
                f"--port={db_port}",
                f"--user={db_user}",
                db_name,
            ],
            stdin=f_in,
            env=mysql_env,
            capture_output=True,
            check=True,
        )
    with zipfile.ZipFile(uploads_zip, "r") as zf:
        zf.extractall(STAGING_PRIVATE)
    res_sec = round(time.perf_counter() - t_res_start, 3)

    # 5. Post-restore integrity verification
    with SessionLocal() as db:
        post_requests = db.execute(
            select(
                m.document_requests.c.id,
                m.document_requests.c.request_number,
                m.document_requests.c.status,
            ).order_by(m.document_requests.c.id)
        ).mappings().all()
        post_files = db.execute(
            select(
                m.stored_files.c.id,
                m.stored_files.c.storage_key,
                m.stored_files.c.sha256_hex,
                m.stored_files.c.storage_status,
            ).order_by(m.stored_files.c.id)
        ).mappings().all()
        post_triggers = [r[0] for r in db.execute(text("SHOW TRIGGERS")).all()]
        alembic_rev = db.scalar(text("SELECT version_num FROM alembic_version"))

    post_tables = inspect(engine).get_table_names()
    hash_checks = []
    for frow in post_files:
        if frow["storage_status"] == "removed":
            continue
        target = STAGING_PRIVATE / frow["storage_key"]
        actual = sha256_file(target) if target.is_file() else None
        assert actual == frow["sha256_hex"], (frow["id"], actual, frow["sha256_hex"])
        hash_checks.append(
            {"file_id": frow["id"], "sha256_match": True}
        )

    assert len(post_requests) == len(pre_requests)
    assert len(post_triggers) == len(pre_triggers) == 22
    assert len(post_tables) == 24

    log_lines.append(
        f"$ mysql {db_name} < db_{db_name}.sql && unzip private_uploads.zip -> .private/staging_uploads\n"
        f"[restore-verified] duration_s={res_sec} alembic_rev={alembic_rev} tables={len(post_tables)} "
        f"triggers={len(post_triggers)} requests={[r['request_number'] for r in post_requests]} "
        f"file_hashes_verified={len(hash_checks)}/{len(hash_checks)}"
    )

    # 6. Verify restored login + UI data + protected file download via live Nginx after restore
    staff_c, _ = login_client("registrar@example.test")
    try:
        r_list = staff_c.get("/api/v1/requests").json()
        assert r_list["total"] == len(pre_requests)
        last_file_id = hash_checks[-1]["file_id"]
        r_dl = staff_c.get(f"/api/v1/files/{last_file_id}")
        assert r_dl.status_code == 200
        log_lines.append(
            f"[post-restore-smoke] GET /api/v1/requests total={r_list['total']}; "
            f"GET /api/v1/files/{last_file_id} status=200"
        )
    finally:
        staff_c.close()

    (LOGS / "backup-restore.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    # Render real verbatim log screenshot (mysql-backup-dump.png) & live restored Flutter UI (mysql-restore-success.png)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        # Verbatim backup/restore log view in Edge
        log_ctx = browser.new_context(viewport={"width": 1280, "height": 720})
        log_page = log_ctx.new_page()
        escaped = html.escape("\n".join(log_lines))
        log_page.set_content(
            f"""<!doctype html><html><body style="margin:0;background:#0f172a;color:#e2e8f0;font-family:Consolas,monospace;padding:24px;font-size:13px;line-height:1.55;">
<div style="color:#38bdf8;font-weight:bold;margin-bottom:12px;">PS C:\\Users\\charl\\Projects\\Flutter\\Student Document Request Tracker\\student_document_request_tracker&gt; backup-restore-rehearsal (sdrt_staging)</div>
<pre style="white-space:pre-wrap;margin:0;">{escaped}</pre></body></html>"""
        )
        log_page.screenshot(path=str(SHOTS / "mysql-backup-dump.png"))
        log_ctx.close()

        # Live restored Flutter Web UI on http://localhost:8080
        ui_ctx = browser.new_context(viewport={"width": 1440, "height": 950})
        page = ui_ctx.new_page()
        page.goto(BASE)
        page.wait_for_selector("flt-semantics-placeholder", state="attached")
        page.locator("flt-semantics-placeholder").evaluate("e => e.click()")
        fields = page.get_by_role("textbox")
        fields.nth(0).click()
        fields.nth(0).press_sequentially("registrar@example.test")
        fields.nth(1).click()
        fields.nth(1).press_sequentially(PASSWORD)
        page.get_by_role("button", name="Sign in", exact=True).click()
        expect(page.get_by_role("button", name="Requests", exact=True)).to_be_visible(
            timeout=15000
        )
        page.get_by_role("button", name="Requests", exact=True).click()
        expect(page.get_by_text("SDRT-2026-000001").first).to_be_visible(timeout=15000)
        time.sleep(1.0)
        page.screenshot(path=str(SHOTS / "mysql-restore-success.png"), full_page=True)
        ui_ctx.close()
        browser.close()

    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "backup_duration_seconds": bak_sec,
        "restore_duration_seconds": res_sec,
        "alembic_revision": alembic_rev,
        "tables_restored": len(post_tables),
        "triggers_restored": len(post_triggers),
        "requests_restored": [r["request_number"] for r in post_requests],
        "file_hashes_verified": len(hash_checks),
        "result": "PASS",
    }
    (VERIFY / "restore-verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main():
    smoke = run_smoke_tests()
    dl = run_protected_download_tests(
        smoke["protected_file"]["file_id"], smoke["protected_file"]["sha256"]
    )
    sched = run_scheduler_restart_test()
    restore = run_backup_and_restore_rehearsal()
    summary = {
        "smoke": {"result": smoke["result"], "checks": smoke["total_checks"]},
        "protected_download": {"result": dl["result"], "cases": len(dl["cases"])},
        "scheduler_restart": sched,
        "backup_restore": restore,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
