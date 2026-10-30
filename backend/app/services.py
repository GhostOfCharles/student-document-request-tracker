from fastapi import APIRouter, Depends, Query
from app import models as m
from app.db import database
from app.auth import user
from app.common import one, rows, clean, fail, page

router = APIRouter(prefix="/api/v1/services", tags=["Published services"])


def configuration(db, service_id, version_id=None, active=False):
    service = one(db, m.document_services, m.document_services.c.id == service_id)
    if not service or (active and not service["is_active"]):
        fail("RESOURCE_NOT_FOUND", "Service unavailable.", 404)
    version = one(
        db,
        m.document_service_versions,
        m.document_service_versions.c.id
        == (version_id or service["current_version_id"]),
        m.document_service_versions.c.service_id == service_id,
        m.document_service_versions.c.version_status == "published",
    )
    if not version:
        fail("RESOURCE_NOT_FOUND", "Published service unavailable.", 404)
    fields = rows(
        db,
        m.service_requirements,
        m.service_requirements.c.service_version_id == version["id"],
        order=m.service_requirements.c.sort_order,
    )
    for field in fields:
        field["required"] = field.pop("is_required")
        field["options"] = [
            {"id": o["id"], "value": o["option_value"], "label": o["option_label"]}
            for o in rows(
                db,
                m.requirement_options,
                m.requirement_options.c.requirement_id == field["id"],
                order=m.requirement_options.c.sort_order,
            )
        ]
    payment = {
        "required": version["payment_required"],
        "amount": version["payment_amount"],
        "currency": version["currency_code"],
        "instructions": version["payment_instructions"],
        "reference_required": version["payment_reference_required"],
        "receipt_required": version["payment_receipt_required"],
    }
    output = {
        k: version[k]
        for k in (
            "id",
            "version_number",
            "name",
            "description",
            "category",
            "eligibility_instructions",
            "processing_days",
        )
    }
    output.update(payment=payment, requirements=fields)
    return clean(
        {
            "id": service_id,
            "service_code": service["service_code"],
            "is_active": service["is_active"],
            "version": output,
        }
    )


@router.get("")
def listing(
    page_number: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = "",
    category: str | None = None,
    actor=Depends(user),
    db=Depends(database),
):
    services = rows(db, m.document_services, m.document_services.c.is_active == True)
    cards = []
    for service in services:
        config = configuration(db, service["id"])["version"]
        if q.lower() not in config["name"].lower() or (
            category and config["category"] != category
        ):
            continue
        cards.append(
            {
                k: config[k]
                for k in ("name", "description", "category", "processing_days")
            }
            | {
                "id": service["id"],
                "payment_required": config["payment"]["required"],
                "requirement_count": len(config["requirements"]),
            }
        )
    start = (page_number - 1) * page_size
    return {
        "items": cards[start : start + page_size],
        "page": page_number,
        "page_size": page_size,
        "total": len(cards),
    }


@router.get("/{service_id}")
def detail(service_id: int, actor=Depends(user), db=Depends(database)):
    return configuration(db, service_id, active=True)
