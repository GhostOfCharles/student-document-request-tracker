"""Run once with python -m app.automation.scheduler, separately from FastAPI."""

import logging
from sqlalchemy import text
from apscheduler.schedulers.blocking import BlockingScheduler
from app.db import engine, SessionLocal, utcnow
from app import models as m
from app.automation.worker import safe_process, recover, event
from app.automation.tasks import scan, cleanup, generate_summary, local_now
from app.common import one


def guarded(fn):
    def run():
        try:
            fn()
        except Exception:
            event("schedule_failed", job_name=fn.__name__, error_code="TASK_FAILED")

    return run


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    lock = engine.connect()
    if lock.scalar(text("SELECT GET_LOCK('sdrt_designated_scheduler',0)")) != 1:
        raise SystemExit("Another scheduler already owns the designated process lock.")

    # A dedicated connection retains the lock for this process lifetime.
    def heartbeat():
        if lock.scalar(
            text("SELECT IS_USED_LOCK('sdrt_designated_scheduler')")
        ) != lock.scalar(text("SELECT CONNECTION_ID()")):
            raise SystemExit("Scheduler ownership lost")

    try:
        with SessionLocal.begin() as db:
            recover(db, utcnow())
            db.execute(
                m.automation_runs.update()
                .where(m.automation_runs.c.status == "running")
                .values(
                    status="failed",
                    finished_at=utcnow(),
                    error_code="WORKER_INTERRUPTED",
                    error_summary="Previous scheduler stopped before run completion.",
                )
            )
        safe_process()
        for task in (scan, cleanup):
            guarded(task)()
        local = local_now()
        with SessionLocal() as db:
            exists = one(
                db,
                m.daily_request_summaries,
                m.daily_request_summaries.c.summary_date == local.date(),
            )
        if local.hour >= 17 and not exists:
            guarded(generate_summary)()
        scheduler = BlockingScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
        )
        scheduler.add_job(heartbeat, "interval", seconds=30, id="ownership_heartbeat")
        scheduler.add_job(safe_process, "interval", minutes=1, id="durable_worker")
        scheduler.add_job(guarded(scan), "interval", minutes=15, id="aging_escalation")
        scheduler.add_job(
            guarded(generate_summary),
            "cron",
            hour=17,
            minute=0,
            timezone="Asia/Manila",
            id="daily_pending_summary",
        )
        scheduler.add_job(
            guarded(cleanup),
            "cron",
            hour=2,
            minute=0,
            timezone="Asia/Manila",
            id="staging_cleanup",
        )
        event("scheduler_started")
        scheduler.start()
    finally:
        lock.execute(text("SELECT RELEASE_LOCK('sdrt_designated_scheduler')"))
        lock.close()


if __name__ == "__main__":
    main()
