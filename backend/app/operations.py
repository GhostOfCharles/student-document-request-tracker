from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from app import models as m, schemas as s
from app.auth import user, staff, verify_csrf
from app.db import database, utcnow
from app.common import one, rows, page, clean, change, audit, fail, utc_filter
from app.requests import requests
from app.automation.tasks import generate_summary, local_now
from app.automation.worker import ALLOWLIST

router = APIRouter(prefix="/api/v1", tags=["Notifications and automation monitoring"])


def job_view(job):
    return {
        k: v
        for k, v in job.items()
        if k not in ("locked_by", "locked_until", "payload_json", "idempotency_key")
    }


@router.get("/dashboard")
def dashboard(actor=Depends(user), db=Depends(database)):
    conditions = (
        [m.document_requests.c.student_user_id == actor["id"]]
        if actor["role"] == "student"
        else []
    )
    counts = dict(
        db.execute(
            select(m.document_requests.c.status, func.count())
            .where(*conditions)
            .group_by(m.document_requests.c.status)
        ).all()
    )
    notifications = db.scalar(
        select(func.count())
        .select_from(m.notifications)
        .where(
            m.notifications.c.recipient_user_id == actor["id"],
            m.notifications.c.read_at.is_(None),
        )
    )
    recent = requests(1, 5, "", None, None, None, None, None, actor, db)["items"]
    result = {
        "counts": counts,
        "recent_requests": recent,
        "unread_notifications": notifications,
    }
    if actor["role"] == "staff":
        result["failed_automation_jobs"] = db.scalar(
            select(func.count())
            .select_from(m.automation_jobs)
            .where(m.automation_jobs.c.status == "failed_permanently")
        )
    return clean(result)


@router.get("/notifications")
def notifications(
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: str = Query("all", pattern="^(all|unread|read)$"),
    actor=Depends(user),
    db=Depends(database),
):
    conditions = [m.notifications.c.recipient_user_id == actor["id"]]
    if state == "unread":
        conditions.append(m.notifications.c.read_at.is_(None))
    if state == "read":
        conditions.append(m.notifications.c.read_at.is_not(None))
    return page(
        db,
        m.notifications,
        conditions,
        page_number,
        page_size,
        transform=lambda r: {
            k: v
            for k, v in r.items()
            if k not in ("recipient_user_id", "event_key", "automation_job_id")
        },
    )


@router.patch(
    "/notifications/{notification_id}/read", dependencies=[Depends(verify_csrf)]
)
def read(notification_id: int, actor=Depends(user), db=Depends(database)):
    record = one(
        db,
        m.notifications,
        m.notifications.c.id == notification_id,
        m.notifications.c.recipient_user_id == actor["id"],
        lock=True,
    )
    if not record:
        fail("RESOURCE_NOT_FOUND", "Notification not found.", 404)
    if not record["read_at"]:
        record["read_at"] = utcnow()
        change(db, m.notifications, record["id"], read_at=record["read_at"])
    return clean(
        {
            k: v
            for k, v in record.items()
            if k not in ("recipient_user_id", "event_key", "automation_job_id")
        }
    )


@router.post("/notifications/read-all", dependencies=[Depends(verify_csrf)])
def read_all(actor=Depends(user), db=Depends(database)):
    result = db.execute(
        m.notifications.update()
        .where(
            m.notifications.c.recipient_user_id == actor["id"],
            m.notifications.c.read_at.is_(None),
        )
        .values(read_at=utcnow())
    )
    return {"updated_count": result.rowcount}


@router.get("/staff/reports/daily")
def report(
    date_value: date | None = Query(None, alias="date"),
    actor=Depends(staff),
    db=Depends(database),
):
    summary = one(
        db,
        m.daily_request_summaries,
        m.daily_request_summaries.c.summary_date == (date_value or local_now().date()),
    )
    if not summary:
        fail("SUMMARY_NOT_GENERATED", "No stored summary exists for this date.", 404)
    return clean(summary)


@router.post("/staff/reports/daily/regenerate", dependencies=[Depends(verify_csrf)])
def regenerate(body: s.SummaryDate, actor=Depends(staff)):
    if body.date != local_now().date():
        fail(
            "VALIDATION_FAILED", "Only the current Asia/Manila date can be regenerated."
        )
    return clean(generate_summary(trigger="manual", actor_id=actor["id"]))


@router.get("/staff/alerts")
def alerts(
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: str = Query("open", pattern="^(open|resolved|all)$"),
    alert_type: str | None = Query(None, pattern="^(aging|escalation)$"),
    request_id: int | None = None,
    actor=Depends(staff),
    db=Depends(database),
):
    conditions = []
    if state != "all":
        conditions.append(
            m.request_alerts.c.resolved_at.is_(None)
            if state == "open"
            else m.request_alerts.c.resolved_at.is_not(None)
        )
    if alert_type:
        conditions.append(m.request_alerts.c.alert_type == alert_type)
    if request_id:
        conditions.append(m.request_alerts.c.request_id == request_id)
    return page(db, m.request_alerts, conditions, page_number, page_size)


@router.get("/staff/automation/runs")
def runs(
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    job_name: str | None = None,
    started_from: str | None = None,
    started_to: str | None = None,
    actor=Depends(staff),
    db=Depends(database),
):
    conditions = []
    if status:
        conditions.append(m.automation_runs.c.status == status)
    if job_name:
        conditions.append(m.automation_runs.c.job_name == job_name)
    if started_from:
        conditions.append(m.automation_runs.c.started_at >= utc_filter(started_from))
    if started_to:
        conditions.append(m.automation_runs.c.started_at < utc_filter(started_to))
    return page(db, m.automation_runs, conditions, page_number, page_size)


@router.get("/staff/automation/jobs")
def jobs(
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    job_type: str | None = None,
    request_id: int | None = None,
    actor=Depends(staff),
    db=Depends(database),
):
    conditions = []
    if status:
        conditions.append(m.automation_jobs.c.status == status)
    if job_type:
        conditions.append(m.automation_jobs.c.job_type == job_type)
    if request_id:
        conditions.append(m.automation_jobs.c.request_id == request_id)
    return page(
        db, m.automation_jobs, conditions, page_number, page_size, transform=job_view
    )


@router.get("/staff/automation/jobs/{job_id}")
def job_detail(job_id: int, actor=Depends(staff), db=Depends(database)):
    record = one(db, m.automation_jobs, m.automation_jobs.c.id == job_id)
    if not record:
        fail("RESOURCE_NOT_FOUND", "Automation job not found.", 404)
    result = job_view(record)
    result["attempts"] = [
        {k: v for k, v in attempt.items() if k != "worker_identifier"}
        for attempt in rows(
            db,
            m.automation_attempts,
            m.automation_attempts.c.automation_job_id == job_id,
            order=m.automation_attempts.c.attempt_number,
        )
    ]
    return clean(result)


@router.post(
    "/staff/automation/jobs/{job_id}/retry", dependencies=[Depends(verify_csrf)]
)
def retry(job_id: int, body: s.Reason, actor=Depends(staff), db=Depends(database)):
    job = one(db, m.automation_jobs, m.automation_jobs.c.id == job_id, lock=True)
    if not job:
        fail("RESOURCE_NOT_FOUND", "Automation job not found.", 404)
    if (
        job["status"] != "failed_permanently"
        or job["job_type"] not in ALLOWLIST
        or job["max_attempts"] >= 9
    ):
        fail(
            "STATUS_CONFLICT", "This job is not eligible for another retry cycle.", 409
        )
    change(
        db,
        m.automation_jobs,
        job_id,
        status="pending",
        max_attempts=job["max_attempts"] + 3,
        next_attempt_at=utcnow(),
        completed_at=None,
    )
    audit(
        db,
        actor["id"],
        "automation_retry",
        "automation_job",
        job_id,
        job_id=job_id,
        details={"reason": body.reason, "max_attempts": job["max_attempts"] + 3},
    )
    return clean(job_view(one(db, m.automation_jobs, m.automation_jobs.c.id == job_id)))


@router.post(
    "/staff/automation/jobs/{job_id}/resolve", dependencies=[Depends(verify_csrf)]
)
def resolve(
    job_id: int, body: s.Resolution, actor=Depends(staff), db=Depends(database)
):
    job = one(db, m.automation_jobs, m.automation_jobs.c.id == job_id, lock=True)
    if not job:
        fail("RESOURCE_NOT_FOUND", "Automation job not found.", 404)
    if job["status"] != "failed_permanently":
        fail(
            "STATUS_CONFLICT", "Only permanent failures can be resolved manually.", 409
        )
    change(
        db,
        m.automation_jobs,
        job_id,
        status="resolved_manually",
        resolved_by_user_id=actor["id"],
        resolved_at=utcnow(),
        resolution_note=body.resolution_note,
    )
    audit(
        db,
        actor["id"],
        "automation_resolved",
        "automation_job",
        job_id,
        job_id=job_id,
        details={"resolution_note": body.resolution_note},
    )
    return clean(job_view(one(db, m.automation_jobs, m.automation_jobs.c.id == job_id)))


@router.get("/staff/audit-logs")
def audits(
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = None,
    request_id: int | None = None,
    result: str | None = None,
    q: str = "",
    actor_user_id: int | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    actor=Depends(staff),
    db=Depends(database),
):
    conditions = []
    if action:
        conditions.append(m.audit_logs.c.action == action)
    if request_id:
        conditions.append(m.audit_logs.c.request_id == request_id)
    if result:
        conditions.append(m.audit_logs.c.result == result)
    if q:
        conditions.append(m.audit_logs.c.action.contains(q, autoescape=True))
    if actor_user_id:
        conditions.append(m.audit_logs.c.actor_user_id == actor_user_id)
    if created_from:
        conditions.append(m.audit_logs.c.created_at >= utc_filter(created_from))
    if created_to:
        conditions.append(m.audit_logs.c.created_at < utc_filter(created_to))
    return page(db, m.audit_logs, conditions, page_number, page_size)
