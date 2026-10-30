import hashlib
import json
from datetime import timedelta
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from app import models as m, schemas as s
from app.auth import user, staff, student, verify_csrf
from app.db import database, utcnow
from app.common import one, rows, add, change, audit, fail, clean, page, utc_filter
from app.services import configuration

router = APIRouter(prefix="/api/v1", tags=["Requests"])


def accessible(db, request_id, actor, lock=False):
    req = one(
        db, m.document_requests, m.document_requests.c.id == request_id, lock=lock
    )
    if not req or (
        actor["role"] == "student" and req["student_user_id"] != actor["id"]
    ):
        fail("RESOURCE_NOT_FOUND", "Request not found.", 404)
    return req


def current_revision(db, req):
    return one(
        db,
        m.request_revisions,
        m.request_revisions.c.request_id == req["id"],
        m.request_revisions.c.revision_number == req["current_revision_number"],
    )


def canonical(body):
    value = body.model_dump(
        mode="json", exclude={"client_submission_key", "expected_row_version"}
    )
    for key in ("answers", "attachments"):
        value[key] = sorted(value[key], key=lambda r: r["requirement_id"])
    value["answers"] = [
        {k: v for k, v in a.items() if v is not None} for a in value["answers"]
    ]
    if value.get("payment") is not None:
        value["payment"] = {k: v for k, v in value["payment"].items() if v is not None}
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).digest()


def creation_result(req, revision, correction_round_id=None):
    # Derive original immutable row_version from append-only history and review events.
    result = {
        "id": req["id"],
        "request_number": req["request_number"],
        "status": "submitted" if revision["revision_number"] == 1 else "under_review",
        "row_version": req["row_version"],
        "revision_number": revision["revision_number"],
        "submitted_at": revision["submitted_at"],
    }
    if correction_round_id:
        result["correction_round_id"] = correction_round_id
    return clean(result)


def replay(db, body, actor, request_id=None):
    revision = one(
        db,
        m.request_revisions,
        m.request_revisions.c.client_submission_key == str(body.client_submission_key),
    )
    if not revision:
        return None
    req = accessible(db, revision["request_id"], actor)
    if request_id and req["id"] != request_id:
        fail("IDEMPOTENCY_CONFLICT", "Submission key already used.", 409)
    if revision["submission_payload_hash"] != canonical(body):
        fail(
            "IDEMPOTENCY_CONFLICT",
            "Submission key was used with different values.",
            409,
        )
    expected_type = "correction" if request_id else "initial"
    if revision["revision_type"] != expected_type:
        fail("IDEMPOTENCY_CONFLICT", "Submission key already used.", 409)
    if expected_type == "initial":
        req["row_version"] = 1
    else:
        # The correction action increments once from the submitted round's row version.
        event = one(
            db,
            m.audit_logs,
            m.audit_logs.c.action == "correction_submitted",
            m.audit_logs.c.target_id == revision["id"],
        )
        req["row_version"] = event["details_json"]["creation_row_version"]
    return creation_result(req, revision, getattr(body, "correction_round_id", None))


def validate_snapshot(db, body, actor, version, request_id=None):
    requirements = rows(
        db,
        m.service_requirements,
        m.service_requirements.c.service_version_id == version["id"],
    )
    answers = {a.requirement_id: a for a in body.answers}
    attachments = {a.requirement_id: a.stored_file_id for a in body.attachments}
    if len(answers) != len(body.answers) or len(attachments) != len(body.attachments):
        fail("VALIDATION_FAILED", "Duplicate requirement identifiers.")
    known = {r["id"] for r in requirements}
    if (set(answers) | set(attachments)) - known:
        fail("VALIDATION_FAILED", "Requirement does not belong to the pinned version.")
    slots = []
    for field in requirements:
        fid = field["id"]
        answer = answers.get(fid)
        file_id = attachments.get(fid)

        def invalid(message):
            fail(
                "VALIDATION_FAILED",
                "One or more requirements are invalid.",
                fields=[{"field": f"requirement_{fid}", "message": message}],
            )

        if field["field_type"] == "file":
            if answer or (field["is_required"] and not file_id):
                invalid("A valid attachment is required.")
            if file_id:
                slots.append((file_id, field))
            continue
        if file_id:
            invalid("This field does not accept a file.")
        if not answer:
            if field["is_required"]:
                invalid("This field is required.")
            continue
        key = {
            "text": "text_value",
            "date": "date_value",
            "checkbox": "boolean_value",
            "select": "selected_option_id",
        }[field["field_type"]]
        value = getattr(answer, key)
        if value is None:
            invalid("Incorrect answer type.")
        if key == "text_value" and (
            len(value) < (field["min_length"] or (1 if field["is_required"] else 0))
            or len(value) > (field["max_length"] or 1000)
        ):
            invalid("Text length is outside the configured limits.")
        if key == "boolean_value" and field["is_required"] and value is not True:
            invalid("Confirm this required statement.")
        if key == "selected_option_id" and not one(
            db,
            m.requirement_options,
            m.requirement_options.c.id == value,
            m.requirement_options.c.requirement_id == fid,
        ):
            invalid("Select a configured option.")
    payment = body.payment
    if not version["payment_required"] and payment is not None:
        fail("VALIDATION_FAILED", "This service does not accept payment evidence.")
    if version["payment_required"]:
        if (
            not payment
            or (version["payment_reference_required"] and not payment.reference)
            or (version["payment_receipt_required"] and not payment.receipt_file_id)
        ):
            fail("VALIDATION_FAILED", "Required fictional payment evidence is missing.")
        if payment.receipt_file_id:
            slots.append((payment.receipt_file_id, None))
    ids = [f for f, _ in slots]
    if len(ids) > 10 or len(set(ids)) != len(ids):
        fail("VALIDATION_FAILED", "Use at most ten distinct files per revision.")
    total = 0
    for file_id, field in sorted(slots, key=lambda pair: pair[0]):
        file = one(db, m.stored_files, m.stored_files.c.id == file_id, lock=True)
        if (
            not file
            or file["uploaded_by_user_id"] != actor["id"]
            or file["storage_status"] == "removed"
        ):
            fail("VALIDATION_FAILED", "Evidence is unavailable.")
        if file["storage_status"] == "staging":
            if file["staging_expires_at"] <= utcnow():
                fail("VALIDATION_FAILED", "Staged evidence expired; upload it again.")
        else:
            linked = (
                db.scalar(
                    select(m.request_revisions.c.id)
                    .where(
                        m.request_revisions.c.request_id == request_id,
                        m.request_revisions.c.payment_receipt_file_id == file_id,
                    )
                    .limit(1)
                )
                if request_id
                else None
            )
            if not linked and request_id:
                linked = db.scalar(
                    select(m.request_attachments.c.id)
                    .join(
                        m.request_revisions,
                        m.request_revisions.c.id == m.request_attachments.c.revision_id,
                    )
                    .where(
                        m.request_revisions.c.request_id == request_id,
                        m.request_attachments.c.stored_file_id == file_id,
                    )
                    .limit(1)
                )
            if not linked:
                fail(
                    "VALIDATION_FAILED",
                    "Submitted evidence belongs to another request.",
                )
        from app.config import settings

        if not (settings.private_dir / file["storage_key"]).is_file():
            fail(
                "VALIDATION_FAILED",
                "Private evidence bytes are missing; contact staff.",
            )
        if field and (
            file["mime_type"] not in field["allowed_mime_types"]
            or file["size_bytes"] > (field["max_file_size_bytes"] or 5242880)
        ):
            fail("VALIDATION_FAILED", "File exceeds the configured policy.")
        total += file["size_bytes"]
    if total > 26214400:
        fail("VALIDATION_FAILED", "Combined file size exceeds 25 MiB.")
    return ids


def save_revision(db, req, body, actor, file_ids):
    payment = body.payment
    rid = add(
        db,
        m.request_revisions,
        request_id=req["id"],
        revision_number=req["current_revision_number"],
        revision_type="initial"
        if req["current_revision_number"] == 1
        else "correction",
        revision_status="submitted",
        payment_reference=payment.reference if payment else None,
        payment_receipt_file_id=payment.receipt_file_id if payment else None,
        submitted_by_user_id=actor["id"],
        submitted_at=utcnow(),
        client_submission_key=str(body.client_submission_key),
        submission_payload_hash=canonical(body),
    )
    for answer in body.answers:
        add(db, m.request_field_values, revision_id=rid, **answer.model_dump())
    for attachment in body.attachments:
        add(db, m.request_attachments, revision_id=rid, **attachment.model_dump())
    for fid in file_ids:
        change(db, m.stored_files, fid, storage_status="ready", staging_expires_at=None)
    return one(db, m.request_revisions, m.request_revisions.c.id == rid)


def queue_status(db, req, revision_id, previous, actor, remarks=None):
    hid = add(
        db,
        m.request_status_history,
        request_id=req["id"],
        revision_id=revision_id,
        previous_status=previous,
        new_status=req["status"],
        changed_by_user_id=actor["id"],
        change_source=actor["role"],
        public_remarks=remarks,
    )
    audit(db, actor["id"], "status_" + req["status"], "request", req["id"], req["id"])
    from app.automation.worker import enqueue

    staff_events = {"submitted", "cancelled", "completed"}
    if previous == "needs_correction":
        staff_events.add("under_review")
    recipients = [req["student_user_id"]]
    if req["status"] in staff_events:
        recipients += [
            r["id"]
            for r in rows(
                db, m.users, m.users.c.role == "staff", m.users.c.is_active == True
            )
        ]
    for uid in set(recipients):
        enqueue(
            db,
            "notification",
            f"status:{hid}:recipient:{uid}",
            request_id=req["id"],
            recipient_user_id=uid,
            payload={
                "title": f"{req['request_number']}: {req['status'].replace('_', ' ')}",
                "notification_type": "request_status",
                "event_key": f"status:{hid}",
            },
        )
    # Resolve alerts immediately when a transition invalidates the predicate.
    if req["status"] in {
        "needs_correction",
        "released",
        "completed",
        "cancelled",
        "rejected",
    }:
        db.execute(
            m.request_alerts.update()
            .where(
                m.request_alerts.c.request_id == req["id"],
                m.request_alerts.c.resolved_at.is_(None),
            )
            .values(resolved_at=utcnow())
        )


def check_action(req, expected, state):
    if req["row_version"] != expected:
        fail(
            "VERSION_CONFLICT", "The request changed. Reload its current details.", 409
        )
    if req["status"] not in state:
        fail(
            "STATUS_CONFLICT", "This action is unavailable in the current status.", 409
        )


def transition(db, req, actor, status, remarks=None):
    old = req["status"]
    now = utcnow()
    req.update(status=status, row_version=req["row_version"] + 1, last_progress_at=now)
    values = {k: req[k] for k in ("status", "row_version", "last_progress_at")}
    if status == "released":
        values.update(released_at=now, released_by_user_id=actor["id"])
    if status == "completed":
        values.update(acknowledged_at=now)
    if status in {"completed", "rejected", "cancelled"}:
        values.update(closed_at=now)
    change(db, m.document_requests, req["id"], **values)
    req.update(values)
    queue_status(db, req, current_revision(db, req)["id"], old, actor, remarks)
    return clean(
        {
            k: req[k]
            for k in (
                "id",
                "request_number",
                "status",
                "row_version",
                "current_revision_number",
                "released_at",
                "released_by_user_id",
                "acknowledged_at",
                "closed_at",
            )
        }
    )


@router.post("/requests", status_code=201, dependencies=[Depends(verify_csrf)])
def submit(
    body: s.Submission, response: Response, actor=Depends(student), db=Depends(database)
):
    repeated = replay(db, body, actor)
    if repeated:
        response.status_code = 200
        return repeated
    try:
        service = one(
            db,
            m.document_services,
            m.document_services.c.id == body.service_id,
            lock=True,
        )
        repeated = replay(db, body, actor)
        if repeated:
            response.status_code = 200
            return repeated
        if (
            not service
            or not service["is_active"]
            or service["current_version_id"] != body.service_version_id
        ):
            fail(
                "SERVICE_VERSION_CHANGED",
                "Reload the active service configuration.",
                409,
            )
        version = one(
            db,
            m.document_service_versions,
            m.document_service_versions.c.id == body.service_version_id,
            m.document_service_versions.c.service_id == body.service_id,
            m.document_service_versions.c.version_status == "published",
        )
        if not version:
            fail("SERVICE_VERSION_CHANGED", "Published version is unavailable.", 409)
        files = validate_snapshot(db, body, actor, version)
        now = utcnow()
        rid = add(
            db,
            m.document_requests,
            request_number="PENDING-" + str(body.client_submission_key)[:28],
            student_user_id=actor["id"],
            service_id=body.service_id,
            service_version_id=version["id"],
            status="submitted",
            current_revision_number=1,
            row_version=1,
            submitted_at=now,
            due_at=now + timedelta(days=version["processing_days"]),
            last_progress_at=now,
            client_submission_key=str(body.client_submission_key),
            submission_payload_hash=canonical(body),
        )
        change(
            db, m.document_requests, rid, request_number=f"SDRT-{now.year}-{rid:06d}"
        )
        req = one(db, m.document_requests, m.document_requests.c.id == rid)
        revision = save_revision(db, req, body, actor, files)
        queue_status(db, req, revision["id"], None, actor)
        db.commit()
        return creation_result(req, revision)
    except IntegrityError:
        db.rollback()
        repeated = replay(db, body, actor)
        if repeated:
            response.status_code = 200
            return repeated
        raise


def revision_view(db, revision):
    def descriptor(fid):
        f = one(db, m.stored_files, m.stored_files.c.id == fid)
        return {k: f[k] for k in ("id", "original_filename", "mime_type", "size_bytes")}

    answers = rows(
        db,
        m.request_field_values,
        m.request_field_values.c.revision_id == revision["id"],
    )
    attachments = [
        {
            "requirement_id": a["requirement_id"],
            "stored_file_id": a["stored_file_id"],
            "file": descriptor(a["stored_file_id"]),
        }
        for a in rows(
            db,
            m.request_attachments,
            m.request_attachments.c.revision_id == revision["id"],
        )
    ]
    result = {
        k: revision[k]
        for k in ("id", "revision_number", "revision_type", "submitted_at")
    }
    result.update(
        answers=[
            {
                k: v
                for k, v in a.items()
                if k not in ("id", "revision_id") and v is not None
            }
            for a in answers
        ],
        attachments=attachments,
        payment={
            "reference": revision["payment_reference"],
            "receipt_file_id": revision["payment_receipt_file_id"],
            "receipt": descriptor(revision["payment_receipt_file_id"])
            if revision["payment_receipt_file_id"]
            else None,
        },
    )
    return clean(result)


@router.get("/requests")
def requests(
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = "",
    status: str | None = None,
    service_id: int | None = None,
    student_number: str | None = None,
    submitted_from: str | None = None,
    submitted_to: str | None = None,
    actor=Depends(user),
    db=Depends(database),
):
    conditions = []
    if actor["role"] == "student":
        conditions.append(m.document_requests.c.student_user_id == actor["id"])
    if q:
        matches = m.document_requests.c.request_number.contains(q, autoescape=True)
        if actor["role"] == "staff":
            matches = or_(
                matches,
                m.document_requests.c.student_user_id.in_(
                    select(m.users.c.id).where(
                        or_(
                            m.users.c.full_name.contains(q, autoescape=True),
                            m.users.c.student_number.contains(q, autoescape=True),
                        )
                    )
                ),
            )
        conditions.append(matches)
    if status:
        conditions.append(m.document_requests.c.status == status)
    if service_id:
        conditions.append(m.document_requests.c.service_id == service_id)
    if student_number:
        if actor["role"] != "staff":
            fail("PERMISSION_DENIED", "Staff filter required.", 403)
        conditions.append(
            m.document_requests.c.student_user_id.in_(
                select(m.users.c.id).where(m.users.c.student_number == student_number)
            )
        )
    if submitted_from:
        conditions.append(
            m.document_requests.c.submitted_at >= utc_filter(submitted_from)
        )
    if submitted_to:
        conditions.append(m.document_requests.c.submitted_at < utc_filter(submitted_to))

    def summary(req):
        v = one(
            db,
            m.document_service_versions,
            m.document_service_versions.c.id == req["service_version_id"],
        )
        return {
            k: req[k]
            for k in (
                "id",
                "request_number",
                "status",
                "row_version",
                "current_revision_number",
                "submitted_at",
                "due_at",
            )
        } | {"service_name": v["name"]}

    return page(
        db, m.document_requests, conditions, page_number, page_size, transform=summary
    )


@router.get("/requests/{request_id}")
def detail(request_id: int, actor=Depends(user), db=Depends(database)):
    req = accessible(db, request_id, actor)
    result = {
        k: v
        for k, v in req.items()
        if k not in ("client_submission_key", "submission_payload_hash")
    }
    revision = current_revision(db, req)
    result["latest_revision"] = revision_view(db, revision)
    result["service"] = configuration(db, req["service_id"], req["service_version_id"])
    review = one(
        db,
        m.payment_reviews,
        m.payment_reviews.c.id
        == select(m.payment_reviews.c.id)
        .where(m.payment_reviews.c.revision_id == revision["id"])
        .order_by(m.payment_reviews.c.reviewed_at.desc(), m.payment_reviews.c.id.desc())
        .limit(1)
        .scalar_subquery(),
    )
    result["payment_outcome"] = review["outcome"] if review else None
    correction = one(
        db,
        m.correction_rounds,
        m.correction_rounds.c.request_id == request_id,
        m.correction_rounds.c.resolved_at.is_(None),
    )
    if correction:
        correction["items"] = rows(
            db,
            m.correction_items,
            m.correction_items.c.correction_round_id == correction["id"],
        )
    result["open_correction_round"] = correction
    if actor["role"] == "staff":
        owner = one(db, m.users, m.users.c.id == req["student_user_id"])
        result["student"] = {k: owner[k] for k in ("id", "full_name", "student_number")}
    return clean(result)


@router.get("/requests/{request_id}/history")
def history(
    request_id: int,
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    actor=Depends(user),
    db=Depends(database),
):
    accessible(db, request_id, actor)

    def event(row):
        return {
            k: v
            for k, v in row.items()
            if actor["role"] == "staff" or k != "internal_remarks"
        }

    return page(
        db,
        m.request_status_history,
        [m.request_status_history.c.request_id == request_id],
        page_number,
        page_size,
        order=m.request_status_history.c.id,
        transform=event,
    )


@router.get("/requests/{request_id}/revisions")
def revisions(
    request_id: int,
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    actor=Depends(user),
    db=Depends(database),
):
    accessible(db, request_id, actor)
    return page(
        db,
        m.request_revisions,
        [m.request_revisions.c.request_id == request_id],
        page_number,
        page_size,
        order=m.request_revisions.c.revision_number,
        transform=lambda r: {
            k: r[k] for k in ("id", "revision_number", "revision_type", "submitted_at")
        },
    )


@router.get("/requests/{request_id}/revisions/{number}")
def revision_detail(
    request_id: int, number: int, actor=Depends(user), db=Depends(database)
):
    accessible(db, request_id, actor)
    revision = one(
        db,
        m.request_revisions,
        m.request_revisions.c.request_id == request_id,
        m.request_revisions.c.revision_number == number,
    )
    if not revision:
        fail("RESOURCE_NOT_FOUND", "Revision not found.", 404)
    return revision_view(db, revision)


@router.post(
    "/requests/{request_id}/correction-submissions",
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
def resubmit(
    request_id: int,
    body: s.CorrectionSubmission,
    response: Response,
    actor=Depends(student),
    db=Depends(database),
):
    repeated = replay(db, body, actor, request_id)
    if repeated:
        response.status_code = 200
        return repeated
    try:
        req = accessible(db, request_id, actor, True)
        repeated = replay(db, body, actor, request_id)
        if repeated:
            response.status_code = 200
            return repeated
        check_action(req, body.expected_row_version, {"needs_correction"})
        cr = one(
            db,
            m.correction_rounds,
            m.correction_rounds.c.id == body.correction_round_id,
            m.correction_rounds.c.request_id == request_id,
            m.correction_rounds.c.resolved_at.is_(None),
            lock=True,
        )
        if not cr:
            fail("STATUS_CONFLICT", "Correction round is no longer open.", 409)
        old = revision_view(db, current_revision(db, req))
        items = rows(
            db, m.correction_items, m.correction_items.c.correction_round_id == cr["id"]
        )
        targets = {
            i["requirement_id"] for i in items if i["target_kind"] == "requirement"
        }
        for key in ("answers", "attachments"):
            prev = {
                a["requirement_id"]: {k: v for k, v in a.items() if k != "file"}
                for a in old[key]
            }
            new = {
                a.requirement_id: a.model_dump(mode="json", exclude_none=True)
                for a in getattr(body, key)
            }
            for fid in set(prev) | set(new):
                if fid not in targets and prev.get(fid) != new.get(fid):
                    fail(
                        "VALIDATION_FAILED",
                        "Only correction-target requirements may change.",
                    )
        pay = body.payment.model_dump(exclude_none=True) if body.payment else {}
        for field, target in [
            ("reference", "payment_reference"),
            ("receipt_file_id", "payment_receipt"),
        ]:
            if not any(i["target_kind"] == target for i in items) and old[
                "payment"
            ].get(field) != pay.get(field):
                fail(
                    "VALIDATION_FAILED",
                    "Only correction-target payment elements may change.",
                )
        version = one(
            db,
            m.document_service_versions,
            m.document_service_versions.c.id == req["service_version_id"],
        )
        files = validate_snapshot(db, body, actor, version, request_id)
        req["current_revision_number"] += 1
        change(
            db,
            m.document_requests,
            request_id,
            current_revision_number=req["current_revision_number"],
            due_at=req["due_at"] + (utcnow() - cr["issued_at"]),
        )
        revision = save_revision(db, req, body, actor, files)
        change(
            db,
            m.correction_rounds,
            cr["id"],
            resolved_at=utcnow(),
            resolved_revision_id=revision["id"],
        )
        transition(db, req, actor, "under_review", "Corrected evidence submitted.")
        audit(
            db,
            actor["id"],
            "correction_submitted",
            "revision",
            revision["id"],
            request_id,
            details={"creation_row_version": req["row_version"]},
        )
        db.commit()
        return creation_result(req, revision, cr["id"])
    except IntegrityError:
        db.rollback()
        repeated = replay(db, body, actor, request_id)
        if repeated:
            response.status_code = 200
            return repeated
        raise


@router.post(
    "/staff/requests/{request_id}/begin-review", dependencies=[Depends(verify_csrf)]
)
def begin_review(
    request_id: int, body: s.Action, actor=Depends(staff), db=Depends(database)
):
    req = accessible(db, request_id, actor, True)
    check_action(req, body.expected_row_version, {"submitted"})
    return transition(db, req, actor, "under_review", body.public_remarks)


@router.post(
    "/staff/requests/{request_id}/payment-reviews",
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
def payment_review(
    request_id: int, body: s.Review, actor=Depends(staff), db=Depends(database)
):
    req = accessible(db, request_id, actor, True)
    check_action(req, body.expected_row_version, {"under_review"})
    revision = current_revision(db, req)
    version = one(
        db,
        m.document_service_versions,
        m.document_service_versions.c.id == req["service_version_id"],
    )
    if not version["payment_required"] or body.revision_id != revision["id"]:
        fail("STATUS_CONFLICT", "Review must target current payable evidence.", 409)
    rid = add(
        db,
        m.payment_reviews,
        revision_id=revision["id"],
        reviewed_by_user_id=actor["id"],
        outcome=body.outcome,
        review_note=body.review_note,
        reviewed_at=utcnow(),
    )
    change(db, m.document_requests, request_id, row_version=req["row_version"] + 1)
    audit(
        db,
        actor["id"],
        "payment_review",
        "request",
        request_id,
        request_id,
        details={"outcome": body.outcome, "revision_id": revision["id"]},
    )
    return {
        "id": rid,
        "outcome": body.outcome,
        "revision_id": revision["id"],
        "row_version": req["row_version"] + 1,
    }


@router.post(
    "/staff/requests/{request_id}/corrections",
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
def corrections(
    request_id: int, body: s.Corrections, actor=Depends(staff), db=Depends(database)
):
    req = accessible(db, request_id, actor, True)
    check_action(req, body.expected_row_version, {"under_review"})
    fields = {
        f["id"]
        for f in rows(
            db,
            m.service_requirements,
            m.service_requirements.c.service_version_id == req["service_version_id"],
        )
    }
    version = one(
        db,
        m.document_service_versions,
        m.document_service_versions.c.id == req["service_version_id"],
    )
    for item in body.items:
        if item.target_kind == "requirement" and item.requirement_id not in fields:
            fail(
                "VALIDATION_FAILED",
                "Correction requirement belongs to another version.",
            )
        if item.target_kind.startswith("payment") and (
            not version["payment_required"]
            or not version[item.target_kind + "_required"]
        ):
            fail("VALIDATION_FAILED", "Payment element is not configured.")
    if one(
        db,
        m.correction_rounds,
        m.correction_rounds.c.request_id == request_id,
        m.correction_rounds.c.resolved_at.is_(None),
    ):
        fail("STATUS_CONFLICT", "A correction is already open.", 409)
    number = (
        db.scalar(
            select(func.count())
            .select_from(m.correction_rounds)
            .where(m.correction_rounds.c.request_id == request_id)
        )
        + 1
    )
    crid = add(
        db,
        m.correction_rounds,
        request_id=request_id,
        round_number=number,
        source_revision_id=current_revision(db, req)["id"],
        issued_by_user_id=actor["id"],
        general_instructions=body.general_instructions,
        issued_at=utcnow(),
    )
    for item in body.items:
        add(db, m.correction_items, correction_round_id=crid, **item.model_dump())
    result = transition(db, req, actor, "needs_correction", body.general_instructions)
    return result | {"correction_round_id": crid}


@router.post(
    "/staff/requests/{request_id}/approve", dependencies=[Depends(verify_csrf)]
)
def approve(
    request_id: int, body: s.Approve, actor=Depends(staff), db=Depends(database)
):
    req = accessible(db, request_id, actor, True)
    check_action(req, body.expected_row_version, {"under_review"})
    if one(
        db,
        m.correction_rounds,
        m.correction_rounds.c.request_id == request_id,
        m.correction_rounds.c.resolved_at.is_(None),
    ):
        fail("STATUS_CONFLICT", "Resolve correction first.", 409)
    version = one(
        db,
        m.document_service_versions,
        m.document_service_versions.c.id == req["service_version_id"],
    )
    if version["payment_required"]:
        review = (
            db.execute(
                select(m.payment_reviews)
                .where(
                    m.payment_reviews.c.revision_id == current_revision(db, req)["id"]
                )
                .order_by(
                    m.payment_reviews.c.reviewed_at.desc(),
                    m.payment_reviews.c.id.desc(),
                )
                .limit(1)
            )
            .mappings()
            .first()
        )
        if not review or review["outcome"] != "verified":
            fail(
                "PAYMENT_NOT_VERIFIED",
                "Verify fictional payment evidence for this revision first.",
                409,
            )
    return transition(db, req, actor, "processing", body.public_remarks)


@router.post("/staff/requests/{request_id}/reject", dependencies=[Depends(verify_csrf)])
def reject(
    request_id: int, body: s.ReasonAction, actor=Depends(staff), db=Depends(database)
):
    req = accessible(db, request_id, actor, True)
    check_action(req, body.expected_row_version, {"under_review"})
    return transition(db, req, actor, "rejected", body.reason)


@router.post(
    "/staff/requests/{request_id}/ready-for-release",
    dependencies=[Depends(verify_csrf)],
)
def ready(request_id: int, body: s.Ready, actor=Depends(staff), db=Depends(database)):
    req = accessible(db, request_id, actor, True)
    check_action(req, body.expected_row_version, {"processing"})
    return transition(db, req, actor, "ready_for_release", body.public_remarks)


@router.post(
    "/staff/requests/{request_id}/release", dependencies=[Depends(verify_csrf)]
)
def release(
    request_id: int, body: s.Release, actor=Depends(staff), db=Depends(database)
):
    req = accessible(db, request_id, actor, True)
    check_action(req, body.expected_row_version, {"ready_for_release"})
    return transition(db, req, actor, "released", body.public_remarks)


@router.post("/requests/{request_id}/acknowledge", dependencies=[Depends(verify_csrf)])
def acknowledge(
    request_id: int, body: s.Acknowledge, actor=Depends(student), db=Depends(database)
):
    req = accessible(db, request_id, actor, True)
    check_action(req, body.expected_row_version, {"released"})
    return transition(db, req, actor, "completed", "Student confirmed receipt.")


@router.post("/requests/{request_id}/cancel", dependencies=[Depends(verify_csrf)])
def cancel(
    request_id: int, body: s.ReasonAction, actor=Depends(student), db=Depends(database)
):
    req = accessible(db, request_id, actor, True)
    check_action(req, body.expected_row_version, {"submitted", "under_review"})
    return transition(db, req, actor, "cancelled", body.reason)


@router.get("/requests/{request_id}/notes")
def notes(
    request_id: int,
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    actor=Depends(user),
    db=Depends(database),
):
    accessible(db, request_id, actor)
    conditions = [m.request_notes.c.request_id == request_id]
    if actor["role"] == "student":
        conditions.append(m.request_notes.c.visibility == "student_visible")
    return page(db, m.request_notes, conditions, page_number, page_size)


@router.post(
    "/staff/requests/{request_id}/notes",
    status_code=201,
    dependencies=[Depends(verify_csrf)],
)
def note(request_id: int, body: s.Note, actor=Depends(staff), db=Depends(database)):
    accessible(db, request_id, actor)
    nid = add(
        db,
        m.request_notes,
        request_id=request_id,
        author_user_id=actor["id"],
        **body.model_dump(),
    )
    audit(
        db,
        actor["id"],
        "note_added",
        "request",
        request_id,
        request_id,
        details={"visibility": body.visibility},
    )
    return clean(one(db, m.request_notes, m.request_notes.c.id == nid))
