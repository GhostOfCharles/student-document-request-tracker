from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, text
from app import models as m
from app.db import SessionLocal, utcnow, engine
from app.config import settings
from app.common import one, rows, add, change, audit
from app.automation.worker import enqueue, event

LOCAL = ZoneInfo("Asia/Manila")
ACTIVE = {"submitted", "under_review", "processing", "ready_for_release"}
PENDING = ACTIVE | {"needs_correction", "released"}


def local_now(now=None):
    return (now or utcnow()).replace(tzinfo=timezone.utc).astimezone(LOCAL)


def new_run(name, trigger="scheduled", now=None):
    now = now or utcnow()
    with SessionLocal.begin() as db:
        return add(
            db,
            m.automation_runs,
            job_name=name,
            trigger_type=trigger,
            scheduled_for=now,
            started_at=now,
            status="running",
            records_scanned=0,
            tasks_created=0,
        )


def failed_run(run_id):
    with SessionLocal.begin() as db:
        change(
            db,
            m.automation_runs,
            run_id,
            status="failed",
            finished_at=utcnow(),
            error_code="TASK_FAILED",
            error_summary="Scheduled operation did not complete; inspect durable work and operator logs.",
        )


def scan(now=None, trigger="scheduled"):
    now = now or utcnow()
    run = new_run("aging_escalation", trigger, now)
    try:
        with engine.connect() as lock, SessionLocal.begin() as db:
            # A named lock serializes manual/test and scheduled scans across processes.
            if lock.scalar(text("SELECT GET_LOCK('sdrt_aging_scan',0)")) != 1:
                raise RuntimeError("SCAN_BUSY")
            try:
                staff = rows(
                    db, m.users, m.users.c.role == "staff", m.users.c.is_active == True
                )
                requests = rows(db, m.document_requests)
                created = 0
                for item in requests:
                    req = one(
                        db,
                        m.document_requests,
                        m.document_requests.c.id == item["id"],
                        lock=True,
                    )
                    aging = req["status"] in ACTIVE and now >= req["due_at"]
                    overdue = aging and now >= req["due_at"] + timedelta(hours=48)
                    stalled = req["status"] in {
                        "submitted",
                        "under_review",
                    } and now >= req["last_progress_at"] + timedelta(hours=72)
                    for kind, predicate, anchor in [
                        ("aging", aging, req["due_at"]),
                        (
                            "escalation",
                            overdue or stalled,
                            req["due_at"] if overdue else req["last_progress_at"],
                        ),
                    ]:
                        key = f"{kind}:{req['id']}:{anchor.isoformat()}"
                        # Resolve old episodes too when the anchor changes.
                        for alert in rows(
                            db,
                            m.request_alerts,
                            m.request_alerts.c.request_id == req["id"],
                            m.request_alerts.c.alert_type == kind,
                            m.request_alerts.c.resolved_at.is_(None),
                        ):
                            if not predicate or alert["idempotency_key"] != key:
                                change(
                                    db, m.request_alerts, alert["id"], resolved_at=now
                                )
                        if not predicate or one(
                            db,
                            m.request_alerts,
                            m.request_alerts.c.idempotency_key == key,
                        ):
                            continue
                        aid = add(
                            db,
                            m.request_alerts,
                            request_id=req["id"],
                            alert_type=kind,
                            idempotency_key=key,
                            request_status_at_trigger=req["status"],
                            triggered_at=now,
                        )
                        first = None
                        for registrar in staff:
                            jid = enqueue(
                                db,
                                "notification",
                                f"{key}:recipient:{registrar['id']}",
                                request_id=req["id"],
                                recipient_user_id=registrar["id"],
                                payload={
                                    "title": f"{kind.title()}: {req['request_number']}",
                                    "event_key": key,
                                    "notification_type": kind,
                                    "reasons": (["overdue_48h"] if overdue else [])
                                    + (["no_progress_72h"] if stalled else []),
                                },
                                run_id=run,
                                now=now,
                            )
                            first = first or jid
                            created += 1
                        change(db, m.request_alerts, aid, automation_job_id=first)
                change(
                    db,
                    m.automation_runs,
                    run,
                    status="succeeded",
                    finished_at=now,
                    records_scanned=len(requests),
                    tasks_created=created,
                )
                db.commit()
            finally:
                lock.execute(text("SELECT RELEASE_LOCK('sdrt_aging_scan')"))
        event(
            "scan_completed",
            run_id=run,
            records_scanned=len(requests),
            tasks_created=created,
        )
        return run
    except Exception:
        failed_run(run)
        raise


def generate_summary(now=None, trigger="scheduled", actor_id=None):
    now = now or utcnow()
    local = local_now(now)
    day = local.date()
    run = new_run("daily_pending_summary", trigger, now)
    try:
        with engine.connect() as lock, SessionLocal() as db:
            # Explicit repeatable-read consistent snapshot for all metrics.
            db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            lock_name = "sdrt_summary_" + day.isoformat()
            if lock.scalar(text("SELECT GET_LOCK(:key,5)"), {"key": lock_name}) != 1:
                raise RuntimeError("SUMMARY_BUSY")
            try:
                requests = rows(db, m.document_requests)
                counts = {
                    status: sum(r["status"] == status for r in requests)
                    for status in PENDING
                }
                midnight = (
                    datetime.combine(day, datetime.min.time(), tzinfo=LOCAL)
                    .astimezone(timezone.utc)
                    .replace(tzinfo=None)
                )
                values = {status + "_count": value for status, value in counts.items()}
                for status in ("completed", "rejected", "cancelled"):
                    values[status + "_today_count"] = sum(
                        r["status"] == status
                        and r["closed_at"] is not None
                        and midnight <= r["closed_at"] <= now
                        for r in requests
                    )
                for kind, column in [
                    ("aging", "aging_count"),
                    ("escalation", "escalated_count"),
                ]:
                    values[column] = db.scalar(
                        select(
                            func.count(func.distinct(m.request_alerts.c.request_id))
                        ).where(
                            m.request_alerts.c.alert_type == kind,
                            m.request_alerts.c.resolved_at.is_(None),
                        )
                    )
                values.update(
                    pending_total=sum(counts.values()),
                    timezone_name="Asia/Manila",
                    generated_at=now,
                    automation_run_id=run,
                )
                summary = one(
                    db,
                    m.daily_request_summaries,
                    m.daily_request_summaries.c.summary_date == day,
                    lock=True,
                )
                if summary:
                    change(db, m.daily_request_summaries, summary["id"], **values)
                    sid = summary["id"]
                else:
                    sid = add(db, m.daily_request_summaries, summary_date=day, **values)
                change(
                    db,
                    m.automation_runs,
                    run,
                    status="succeeded",
                    finished_at=now,
                    records_scanned=len(requests),
                    tasks_created=0,
                )
                audit(
                    db,
                    actor_id,
                    "summary_generated",
                    "daily_summary",
                    sid,
                    details={"summary_date": day.isoformat(), "trigger": trigger},
                )
                db.commit()
                return one(
                    db, m.daily_request_summaries, m.daily_request_summaries.c.id == sid
                )
            finally:
                lock.execute(text("SELECT RELEASE_LOCK(:key)"), {"key": lock_name})
    except Exception:
        failed_run(run)
        raise


def cleanup(now=None):
    from app.files import referenced

    now = now or utcnow()
    run = new_run("staging_cleanup", now=now)
    removed = 0
    try:
        with SessionLocal.begin() as db:
            records = rows(db, m.stored_files)
            for record in records:
                file = one(
                    db, m.stored_files, m.stored_files.c.id == record["id"], lock=True
                )
                if (
                    file["storage_status"] == "staging"
                    and file["staging_expires_at"] <= now
                    and not referenced(db, file["id"])
                ):
                    change(db, m.stored_files, file["id"], storage_status="removed")
                    removed += 1
            change(
                db,
                m.automation_runs,
                run,
                status="succeeded",
                finished_at=now,
                records_scanned=len(records),
                tasks_created=removed,
            )
        # Deletion is retried every cleanup for removed metadata after a crash.
        with SessionLocal() as db:
            for file in rows(
                db, m.stored_files, m.stored_files.c.storage_status == "removed"
            ):
                (settings.private_dir / file["storage_key"]).unlink(missing_ok=True)
            keys = {f["storage_key"] for f in rows(db, m.stored_files)}
        if settings.private_dir.exists():
            for path in settings.private_dir.iterdir():
                if (
                    path.is_file()
                    and path.name not in keys
                    and path.stat().st_mtime
                    < (now - timedelta(hours=24))
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                ):
                    path.unlink()
        return run
    except Exception:
        failed_run(run)
        raise
