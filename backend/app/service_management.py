"""Registrar-managed drafts and immutable published service versions."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import models as m
from app.auth import staff, verify_csrf
from app.automation.worker import enqueue
from app.common import add, audit, change, clean, fail, one, rows
from app.db import database, utcnow
from app.service_schemas import Availability, CreateService, PublishDraft, SaveDraft
from app.services import configuration

router = APIRouter(prefix="/api/v1/staff/services", tags=["Service management"])


def manager(actor=Depends(staff)):
    if not actor["can_manage_services"]:
        fail("PERMISSION_DENIED", "Service management permission is required.", 403)
    return actor


def identity(db, service_id, lock=False):
    service = one(db, m.document_services, m.document_services.c.id == service_id, lock=lock)
    if not service:
        fail("RESOURCE_NOT_FOUND", "Service not found.", 404)
    return service


def draft(db, service_id, lock=False):
    return one(
        db, m.document_service_versions,
        m.document_service_versions.c.service_id == service_id,
        m.document_service_versions.c.version_status == "draft",
        lock=lock,
    )


def draft_response(db, service, version):
    fields = rows(
        db, m.service_requirements,
        m.service_requirements.c.service_version_id == version["id"],
        order=m.service_requirements.c.sort_order,
    )
    for field in fields:
        field["required"] = field.pop("is_required")
        field["options"] = [
            {"id": o["id"], "value": o["option_value"], "label": o["option_label"]}
            for o in rows(db, m.requirement_options, m.requirement_options.c.requirement_id == field["id"], order=m.requirement_options.c.sort_order)
        ]
    result = {
        k: version[k] for k in (
            "id", "version_number", "row_version", "name", "description",
            "category", "eligibility_instructions", "processing_days",
        )
    }
    result["payment"] = {
        "required": version["payment_required"], "amount": version["payment_amount"],
        "currency": version["currency_code"], "instructions": version["payment_instructions"],
        "reference_required": version["payment_reference_required"],
        "receipt_required": version["payment_receipt_required"],
    }
    result["requirements"] = fields
    return clean({"id": service["id"], "service_code": service["service_code"],
                  "is_active": service["is_active"], "version": result})


def values(config):
    payment = config.payment
    return {
        "name": config.name, "description": config.description or None,
        "category": config.category or None,
        "eligibility_instructions": config.eligibility_instructions or None,
        "processing_days": config.processing_days,
        "payment_required": payment.required, "payment_amount": payment.amount,
        "currency_code": payment.currency, "payment_instructions": payment.instructions or None,
        "payment_reference_required": payment.reference_required,
        "payment_receipt_required": payment.receipt_required,
    }


def write_fields(db, version_id, requirements):
    for index, field in enumerate(requirements, 1):
        field_id = add(
            db, m.service_requirements, service_version_id=version_id,
            field_key=field.field_key, label=field.label, help_text=field.help_text or None,
            field_type=field.field_type, is_required=field.required, sort_order=index,
            min_length=field.min_length, max_length=field.max_length,
            allowed_mime_types=field.allowed_mime_types, max_file_size_bytes=field.max_file_size_bytes,
        )
        for order, option in enumerate(field.options, 1):
            add(db, m.requirement_options, requirement_id=field_id, option_value=option.value,
                option_label=option.label, sort_order=order)


def announce(db, service_id, version_id):
    # The recipient/event key is stable across publication and later activation.
    event_key = f"service_published:{service_id}:{version_id}"
    students = rows(db, m.users, m.users.c.role == "student", m.users.c.is_active.is_(True))
    for recipient in students:
        enqueue(
            db, "notification", f"{event_key}:recipient:{recipient['id']}",
            recipient_user_id=recipient["id"],
            payload={"notification_type": "service_published", "event_key": event_key,
                     "service_id": service_id, "service_version_id": version_id,
                     "title": "A document service is available"},
        )


@router.get("")
def list_services(
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = "",
    availability: str = Query("all", pattern="^(all|active|inactive)$"),
    actor=Depends(staff), db=Depends(database),
):
    items = []
    for service in rows(db, m.document_services, order=m.document_services.c.id.desc()):
        if availability != "all" and service["is_active"] != (availability == "active"):
            continue
        published = (
            configuration(db, service["id"], service["current_version_id"])["version"]
            if service["current_version_id"] else None
        )
        draft_version = draft(db, service["id"])
        draft_name = draft_version["name"] if actor["can_manage_services"] and draft_version else ""
        if q.lower() not in (service["service_code"] + " " + (published or {}).get("name", "") + " " + draft_name).lower():
            continue
        items.append({
            "id": service["id"], "service_code": service["service_code"],
            "is_active": service["is_active"], "current_version_id": service["current_version_id"],
            "current_version": published, "has_draft": bool(draft_version),
            **({"draft_name": draft_name} if actor["can_manage_services"] else {}),
        })
    start = (page_number - 1) * page_size
    return clean({"items": items[start:start + page_size], "page": page_number,
                  "page_size": page_size, "total": len(items)})


@router.post("", status_code=201, dependencies=[Depends(verify_csrf)])
def create_service(body: CreateService, actor=Depends(manager), db=Depends(database)):
    if any(r.id or any(o.id for o in r.options) for r in body.configuration.requirements):
        fail("VALIDATION_FAILED", "New service fields cannot include existing IDs.")
    if one(db, m.document_services, m.document_services.c.service_code == body.service_code):
        fail("DUPLICATE_RESOURCE", "A service with that code already exists.", 409)
    try:
        service_id = add(db, m.document_services, service_code=body.service_code,
                         is_active=False, current_version_id=None, created_by_user_id=actor["id"])
        version_id = add(db, m.document_service_versions, service_id=service_id, version_number=1,
                         version_status="draft", created_by_user_id=actor["id"], row_version=1,
                         **values(body.configuration))
        write_fields(db, version_id, body.configuration.requirements)
        audit(db, actor["id"], "service_draft_created", "document_service", service_id)
        return draft_response(db, identity(db, service_id), draft(db, service_id))
    except IntegrityError:
        db.rollback()
        fail("DUPLICATE_RESOURCE", "A service with that code already exists.", 409)


@router.get("/{service_id}")
def service_detail(service_id: int, actor=Depends(staff), db=Depends(database)):
    service = identity(db, service_id)
    versions = rows(db, m.document_service_versions,
                    m.document_service_versions.c.service_id == service_id,
                    m.document_service_versions.c.version_status == "published",
                    order=m.document_service_versions.c.version_number.desc())
    return clean({"id": service_id, "service_code": service["service_code"],
                  "is_active": service["is_active"], "current_version_id": service["current_version_id"],
                  "published_versions": [configuration(db, service_id, v["id"])["version"] for v in versions]})


@router.get("/{service_id}/draft")
def get_draft(service_id: int, actor=Depends(manager), db=Depends(database)):
    service = identity(db, service_id)
    version = draft(db, service_id)
    if not version:
        fail("RESOURCE_NOT_FOUND", "No editable draft exists.", 404)
    return draft_response(db, service, version)


@router.post("/{service_id}/draft", status_code=201, dependencies=[Depends(verify_csrf)])
def create_draft(service_id: int, actor=Depends(manager), db=Depends(database)):
    service = identity(db, service_id, lock=True)
    if draft(db, service_id, lock=True):
        fail("DRAFT_ALREADY_EXISTS", "An editable draft already exists.", 409)
    current_id = service["current_version_id"]
    latest = db.scalar(select(func.max(m.document_service_versions.c.version_number))
                       .where(m.document_service_versions.c.service_id == service_id)) or 0
    if not current_id:
        add(
            db, m.document_service_versions, service_id=service_id, version_number=latest + 1,
            version_status="draft", created_by_user_id=actor["id"], row_version=1,
            name="Untitled service", description=None, category=None, eligibility_instructions=None,
            processing_days=1, payment_required=False, payment_amount=None, currency_code="PHP",
            payment_instructions=None, payment_reference_required=False, payment_receipt_required=False,
        )
        audit(db, actor["id"], "service_draft_created", "document_service", service_id)
        return draft_response(db, service, draft(db, service_id))
    current = one(db, m.document_service_versions, m.document_service_versions.c.id == current_id)
    copy_columns = (
        "name", "description", "category", "eligibility_instructions", "processing_days",
        "payment_required", "payment_amount", "currency_code", "payment_instructions",
        "payment_reference_required", "payment_receipt_required",
    )
    version_id = add(db, m.document_service_versions, service_id=service_id, version_number=latest + 1,
                     version_status="draft", created_by_user_id=actor["id"], row_version=1,
                     **{k: current[k] for k in copy_columns})
    for old in rows(db, m.service_requirements, m.service_requirements.c.service_version_id == current_id,
                    order=m.service_requirements.c.sort_order):
        field_id = add(db, m.service_requirements, service_version_id=version_id,
                       **{k: old[k] for k in ("field_key", "label", "help_text", "field_type", "is_required",
                                              "sort_order", "min_length", "max_length", "allowed_mime_types",
                                              "max_file_size_bytes")})
        for option in rows(db, m.requirement_options, m.requirement_options.c.requirement_id == old["id"]):
            add(db, m.requirement_options, requirement_id=field_id,
                option_value=option["option_value"], option_label=option["option_label"],
                sort_order=option["sort_order"])
    audit(db, actor["id"], "service_draft_created", "document_service", service_id)
    return draft_response(db, service, draft(db, service_id))


@router.put("/{service_id}/draft", dependencies=[Depends(verify_csrf)])
def save_draft(service_id: int, body: SaveDraft, actor=Depends(manager), db=Depends(database)):
    service = identity(db, service_id, lock=True)
    version = draft(db, service_id, lock=True)
    if not version:
        fail("RESOURCE_NOT_FOUND", "No editable draft exists.", 404)
    if version["row_version"] != body.expected_row_version:
        fail("VERSION_CONFLICT", "The draft changed. Reload before saving.", 409)
    existing = rows(db, m.service_requirements, m.service_requirements.c.service_version_id == version["id"])
    fields_by_id = {item["id"]: item for item in existing}
    submitted_ids = [f.id for f in body.configuration.requirements if f.id]
    if len(submitted_ids) != len(set(submitted_ids)) or any(i not in fields_by_id for i in submitted_ids):
        fail("VALIDATION_FAILED", "A requirement does not belong to this draft.")
    option_ids = set()
    for field in body.configuration.requirements:
        for option in field.options:
            if option.id:
                if option.id in option_ids or not field.id or not one(
                    db, m.requirement_options, m.requirement_options.c.id == option.id,
                    m.requirement_options.c.requirement_id == field.id,
                ):
                    fail("VALIDATION_FAILED", "An option does not belong to this draft field.")
                option_ids.add(option.id)
    ids = list(fields_by_id)
    if ids:
        db.execute(m.requirement_options.delete().where(m.requirement_options.c.requirement_id.in_(ids)))
        db.execute(m.service_requirements.delete().where(m.service_requirements.c.id.in_(ids)))
    change(db, m.document_service_versions, version["id"], row_version=version["row_version"] + 1,
           **values(body.configuration))
    write_fields(db, version["id"], body.configuration.requirements)
    audit(db, actor["id"], "service_draft_saved", "document_service", service_id)
    return draft_response(db, service, draft(db, service_id))


@router.post("/{service_id}/publish", dependencies=[Depends(verify_csrf)])
def publish(service_id: int, body: PublishDraft, actor=Depends(manager), db=Depends(database)):
    service = identity(db, service_id, lock=True)
    version = draft(db, service_id, lock=True)
    if not version:
        fail("RESOURCE_NOT_FOUND", "No editable draft exists.", 404)
    if version["row_version"] != body.expected_row_version:
        fail("VERSION_CONFLICT", "The draft changed. Reload before publishing.", 409)
    # Revalidate persisted configuration before freezing the draft.
    from app.service_schemas import ServiceConfigurationInput
    from pydantic import ValidationError
    draft_view = draft_response(db, service, version)["version"]
    input_fields = []
    for field in draft_view["requirements"]:
        input_fields.append({k: field[k] for k in (
            "id", "field_key", "label", "help_text", "field_type", "required",
            "min_length", "max_length", "allowed_mime_types", "max_file_size_bytes", "options",
        )})
    try:
        ServiceConfigurationInput.model_validate({**{k: draft_view[k] for k in (
            "name", "description", "category", "eligibility_instructions", "processing_days", "payment",
        )}, "requirements": input_fields})
    except ValidationError:
        fail("VALIDATION_FAILED", "The draft is incomplete or invalid.")
    change(db, m.document_service_versions, version["id"], version_status="published", published_at=utcnow())
    active = service["is_active"] or body.activate
    change(db, m.document_services, service_id, current_version_id=version["id"], is_active=active)
    if active:
        announce(db, service_id, version["id"])
    audit(db, actor["id"], "service_published", "document_service", service_id,
          details={"version_id": version["id"], "active": active})
    return configuration(db, service_id, version["id"])


@router.patch("/{service_id}/availability", dependencies=[Depends(verify_csrf)])
def availability(service_id: int, body: Availability, actor=Depends(manager), db=Depends(database)):
    service = identity(db, service_id, lock=True)
    if service["current_version_id"] != body.expected_current_version_id:
        fail("VERSION_CONFLICT", "The published version changed. Reload before updating availability.", 409)
    if body.is_active and not service["current_version_id"]:
        fail("STATUS_CONFLICT", "Publish a service before activating it.", 409)
    change(db, m.document_services, service_id, is_active=body.is_active)
    if body.is_active and not service["is_active"]:
        announce(db, service_id, service["current_version_id"])
    audit(db, actor["id"], "service_availability_changed", "document_service", service_id,
          details={"is_active": body.is_active})
    return {"id": service_id, "is_active": body.is_active, "current_version_id": service["current_version_id"]}
