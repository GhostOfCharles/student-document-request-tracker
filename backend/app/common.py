import uuid
from datetime import datetime, date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select, func
from app.db import utcnow
from app import models as m


def fail(code, detail, status=422, fields=None):
    raise HTTPException(
        status,
        {
            "code": code,
            "detail": detail,
            "field_errors": fields or [],
            "trace_id": uuid.uuid4().hex[:12],
        },
    )


def utc_filter(value):
    from datetime import timezone

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (
            parsed.astimezone(timezone.utc).replace(tzinfo=None)
            if parsed.tzinfo
            else parsed
        )
    except ValueError:
        fail("VALIDATION_FAILED", "Use ISO 8601 UTC timestamps or YYYY-MM-DD dates.")


def one(db, table, *where, lock=False):
    stmt = select(table).where(*where)
    if lock:
        stmt = stmt.with_for_update()
    row = db.execute(stmt).mappings().first()
    return dict(row) if row else None


def rows(db, table, *where, order=None):
    stmt = select(table).where(*where)
    if order is not None:
        stmt = stmt.order_by(order)
    return [dict(r) for r in db.execute(stmt).mappings()]


def add(db, table, **values):
    now = utcnow()
    for col in ("created_at", "updated_at"):
        if col in table.c and col not in values:
            values[col] = now
    result = db.execute(table.insert().values(**values))
    return result.inserted_primary_key[0]


def change(db, table, row_id, **values):
    if "updated_at" in table.c:
        values["updated_at"] = utcnow()
    db.execute(table.update().where(table.c.id == row_id).values(**values))


def audit(
    db,
    actor,
    action,
    target_type,
    target_id=None,
    request_id=None,
    job_id=None,
    details=None,
    result="success",
):
    add(
        db,
        m.audit_logs,
        actor_user_id=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        request_id=request_id,
        automation_job_id=job_id,
        result=result,
        details_json=details,
    )


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds") + "Z"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def page(db, table, conditions=(), page=1, page_size=20, order=None, transform=None):
    total = db.scalar(select(func.count()).select_from(table).where(*conditions))
    stmt = (
        select(table)
        .where(*conditions)
        .order_by(order if order is not None else table.c.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [dict(r) for r in db.execute(stmt).mappings()]
    return clean(
        {
            "items": [transform(r) for r in items] if transform else items,
            "page": page,
            "page_size": page_size,
            "total": total,
        }
    )
