"""Durable outbox worker. All handlers are bounded local database operations."""

import json
import logging
import socket
import uuid
from datetime import timedelta
from sqlalchemy import select, and_
from app import models as m
from app.db import SessionLocal, utcnow
from app.common import one, add, change, rows, audit
from app.config import settings

log = logging.getLogger("sdrt.automation")
WORKER = f"{socket.gethostname()}:{uuid.uuid4().hex[:12]}"
ALLOWLIST = {"notification"}


def event(name, **data):
    log.info(
        json.dumps(
            {"timestamp": utcnow().isoformat() + "Z", "event": name, **data},
            sort_keys=True,
        )
    )


def enqueue(
    db,
    job_type,
    key,
    request_id=None,
    recipient_user_id=None,
    payload=None,
    run_id=None,
    now=None,
):
    existing = one(db, m.automation_jobs, m.automation_jobs.c.idempotency_key == key)
    if existing:
        return existing["id"]
    now = now or utcnow()
    return add(
        db,
        m.automation_jobs,
        job_type=job_type,
        idempotency_key=key,
        request_id=request_id,
        recipient_user_id=recipient_user_id,
        payload_json=payload or {},
        automation_run_id=run_id,
        status="pending",
        attempt_count=0,
        max_attempts=3,
        next_attempt_at=now,
        created_at=now,
        updated_at=now,
    )


def surface_failure(db, job_id, now):
    # Bounded direct in-app notices have no follow-up job and cannot recurse.
    key = f"automation_failure:{job_id}"
    for recipient in rows(
        db, m.users, m.users.c.role == "staff", m.users.c.is_active == True
    ):
        if not one(
            db,
            m.notifications,
            m.notifications.c.recipient_user_id == recipient["id"],
            m.notifications.c.event_key == key,
        ):
            add(
                db,
                m.notifications,
                recipient_user_id=recipient["id"],
                notification_type="automation_failure",
                automation_job_id=job_id,
                event_key=key,
                title=f"Automation job {job_id} requires staff action",
                message="Inspect Automation monitoring for the safe error and available recovery actions.",
                created_at=now,
            )


def recover(db, now):
    jobs = rows(
        db,
        m.automation_jobs,
        m.automation_jobs.c.status == "running",
        m.automation_jobs.c.locked_until <= now,
    )
    for item in jobs:
        job = one(
            db,
            m.automation_jobs,
            m.automation_jobs.c.id == item["id"],
            m.automation_jobs.c.status == "running",
            m.automation_jobs.c.locked_until <= now,
            lock=True,
        )
        if not job:
            continue
        attempt = one(
            db,
            m.automation_attempts,
            m.automation_attempts.c.automation_job_id == job["id"],
            m.automation_attempts.c.attempt_number == job["attempt_count"],
        )
        if attempt and attempt["outcome"] == "running":
            change(
                db,
                m.automation_attempts,
                attempt["id"],
                outcome="interrupted",
                finished_at=now,
                error_code="WORKER_INTERRUPTED",
                error_summary="Worker lease expired before completion.",
                duration_ms=max(
                    0, int((now - attempt["started_at"]).total_seconds() * 1000)
                ),
            )
        terminal = job["attempt_count"] >= job["max_attempts"]
        change(
            db,
            m.automation_jobs,
            job["id"],
            status="failed_permanently" if terminal else "pending",
            locked_by=None,
            locked_until=None,
            next_attempt_at=now,
            last_error_code="WORKER_INTERRUPTED",
            last_error_summary="Worker lease expired before completion.",
            completed_at=now if terminal else None,
        )
        if terminal:
            surface_failure(db, job["id"], now)
        event(
            "lease_recovered",
            job_id=job["id"],
            attempt=job["attempt_count"],
            terminal=terminal,
        )


def claim(now=None, worker=WORKER):
    now = now or utcnow()
    with SessionLocal.begin() as db:
        recover(db, now)
        job = (
            db.execute(
                select(m.automation_jobs)
                .where(
                    m.automation_jobs.c.status == "pending",
                    m.automation_jobs.c.next_attempt_at <= now,
                    m.automation_jobs.c.attempt_count
                    < m.automation_jobs.c.max_attempts,
                )
                .order_by(m.automation_jobs.c.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            .mappings()
            .first()
        )
        if not job:
            return None
        job = dict(job)
        number = job["attempt_count"] + 1
        change(
            db,
            m.automation_jobs,
            job["id"],
            status="running",
            attempt_count=number,
            locked_by=worker,
            locked_until=now + timedelta(seconds=120),
        )
        aid = add(
            db,
            m.automation_attempts,
            automation_job_id=job["id"],
            attempt_number=number,
            worker_identifier=worker,
            started_at=now,
            outcome="running",
        )
        event("claimed", job_id=job["id"], attempt=number)
        return {
            "job_id": job["id"],
            "attempt_id": aid,
            "attempt_number": number,
            "worker": worker,
        }


def renew(claimed, now=None):
    """Renew every 30 seconds if a future handler adds bounded long-running work."""
    now = now or utcnow()
    with SessionLocal.begin() as db:
        job = one(
            db,
            m.automation_jobs,
            m.automation_jobs.c.id == claimed["job_id"],
            lock=True,
        )
        if (
            not job
            or job["status"] != "running"
            or job["locked_by"] != claimed["worker"]
            or job["locked_until"] <= now
            or job["attempt_count"] != claimed["attempt_number"]
        ):
            return False
        change(
            db, m.automation_jobs, job["id"], locked_until=now + timedelta(seconds=120)
        )
        return True


class PermanentFailure(Exception):
    pass


class TransientFailure(Exception):
    pass


def deliver(db, job, now):
    if job["job_type"] not in ALLOWLIST:
        raise PermanentFailure("UNSUPPORTED_JOB_TYPE")
    payload = job["payload_json"] or {}
    # Failure injection is internal/test-only; no HTTP endpoint accepts it.
    if settings.environment == "test":
        if payload.get("_test_transient") and job["attempt_count"] == 1:
            raise TransientFailure("TEST_TEMPORARY_UNAVAILABLE")
        if payload.get("_test_always_transient"):
            raise TransientFailure("TEST_TEMPORARY_UNAVAILABLE")
        if payload.get("_test_permanent"):
            raise PermanentFailure("TEST_INVALID_CONFIGURATION")
    recipient = one(db, m.users, m.users.c.id == job["recipient_user_id"])
    if not recipient or not recipient["is_active"]:
        raise PermanentFailure("RECIPIENT_UNAUTHORIZED")
    if job["request_id"]:
        req = one(
            db, m.document_requests, m.document_requests.c.id == job["request_id"]
        )
        if not req or (
            recipient["role"] == "student" and recipient["id"] != req["student_user_id"]
        ):
            raise PermanentFailure("RECIPIENT_UNAUTHORIZED")
    elif recipient["role"] != "staff":
        raise PermanentFailure("RECIPIENT_UNAUTHORIZED")
    if (
        payload.get("notification_type") in {"aging", "escalation"}
        and recipient["role"] != "staff"
    ):
        raise PermanentFailure("RECIPIENT_UNAUTHORIZED")
    if not payload.get("event_key") or not payload.get("title"):
        raise PermanentFailure("INVALID_CONFIGURATION")
    existing = one(
        db,
        m.notifications,
        m.notifications.c.recipient_user_id == recipient["id"],
        m.notifications.c.event_key == payload["event_key"],
    )
    if not existing:
        add(
            db,
            m.notifications,
            recipient_user_id=recipient["id"],
            notification_type=payload.get("notification_type", "request_status"),
            request_id=job["request_id"],
            automation_job_id=job["id"],
            event_key=payload["event_key"],
            title=payload["title"][:180],
            message="Open the authorized record to review details.",
            created_at=now,
        )


def finish(claimed, now=None):
    now = now or utcnow()
    with SessionLocal.begin() as db:
        job = one(
            db,
            m.automation_jobs,
            m.automation_jobs.c.id == claimed["job_id"],
            lock=True,
        )
        if (
            not job
            or job["status"] != "running"
            or job["locked_by"] != claimed["worker"]
            or job["locked_until"] <= now
            or job["attempt_count"] != claimed["attempt_number"]
        ):
            event("stale_finalization_rejected", job_id=claimed["job_id"])
            return False
        attempt = one(
            db,
            m.automation_attempts,
            m.automation_attempts.c.id == claimed["attempt_id"],
        )
        code = None
        outcome = "succeeded"
        status = "succeeded"
        try:
            # Roll back handler writes on failure, but retain the prior durable claim.
            with db.begin_nested():
                deliver(db, job, now)
        except PermanentFailure as exc:
            code = str(exc)
            outcome = "permanent_failure"
            status = "failed_permanently"
        except TransientFailure as exc:
            code = str(exc)
            outcome = "transient_failure"
            status = (
                "failed_permanently"
                if job["attempt_count"] >= job["max_attempts"]
                else "pending"
            )
        # Unexpected/database errors leave the durable lease to expire; the outer caller logs a safe code.
        delay = 1 if job["attempt_count"] % 3 == 1 else 5
        summary = (
            "A bounded automation operation failed; staff should inspect its safe code."
            if code
            else None
        )
        change(
            db,
            m.automation_attempts,
            attempt["id"],
            finished_at=now,
            outcome=outcome,
            error_code=code,
            error_summary=summary,
            duration_ms=max(
                0, int((now - attempt["started_at"]).total_seconds() * 1000)
            ),
        )
        change(
            db,
            m.automation_jobs,
            job["id"],
            status=status,
            next_attempt_at=now + timedelta(minutes=delay)
            if status == "pending"
            else job["next_attempt_at"],
            locked_by=None,
            locked_until=None,
            last_error_code=code,
            last_error_summary=summary,
            completed_at=now if status != "pending" else None,
        )
        if status == "failed_permanently":
            audit(
                db,
                None,
                "automation_failed",
                "automation_job",
                job["id"],
                job_id=job["id"],
                details={"error_code": code},
                result="failure",
            )
            surface_failure(db, job["id"], now)
        event(
            "attempt_finished",
            job_id=job["id"],
            attempt=job["attempt_count"],
            outcome=outcome,
            job_status=status,
            error_code=code,
        )
        return True


def process(now=None, limit=100):
    count = 0
    for _ in range(limit):
        claimed = claim(now)
        if not claimed:
            break
        finish(claimed, now)
        count += 1
    return count


def safe_process():
    try:
        process()
    except Exception:
        event("worker_unavailable", error_code="WORKER_DEPENDENCY_UNAVAILABLE")
