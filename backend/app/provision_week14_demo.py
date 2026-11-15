"""Create draft service templates for service management."""

from sqlalchemy.engine import make_url

from app import models as m
from app.common import add, audit, change, one
from app.config import settings
from app.db import SessionLocal
from app.service_management import values, write_fields
from app.service_schemas import ServiceConfigurationInput


def main():
    url = make_url(settings.database_url)
    if settings.environment != "development" or url.host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("This command only supports a local development database.")
    with SessionLocal.begin() as db:
        staff = one(db, m.users, m.users.c.email == "registrar@example.test",
                    m.users.c.role == "staff", lock=True)
        if not staff:
            raise SystemExit("Seed the controlled registrar account first.")
        change(db, m.users, staff["id"], can_manage_services=True)
        audit(db, staff["id"], "demo_service_management_enabled", "user", staff["id"])
        for code, name, desc in [
            ("DRAFT_ENROLLMENT", "Certificate of Enrollment (Draft)", "Standard document confirming current term enrollment and course load."),
            ("DRAFT_TRANSCRIPT", "Transcript of Records (Draft)", "Official academic transcript of completed courses and grades."),
        ]:
            if one(db, m.document_services, m.document_services.c.service_code == code):
                continue
            config = ServiceConfigurationInput.model_validate({
                "name": name,
                "description": desc,
                "category": "Academic Records",
                "eligibility_instructions": (
                    "Review all document requirements, processing timeline, and payment guidelines before publishing."
                ),
                "processing_days": 3,
                "payment": {"required": False, "amount": None, "currency": "PHP",
                            "instructions": None, "reference_required": False, "receipt_required": False},
                "requirements": [
                    {"field_key": "purpose", "label": "Purpose of request", "field_type": "text",
                     "required": True, "max_length": 200, "options": []},
                    {"field_key": "academic_year", "label": "Academic year or term",
                     "help_text": "Indicate current academic school year and semester.",
                     "field_type": "text", "required": True, "max_length": 100, "options": []},
                    {"field_key": "supporting_document", "label": "Supporting document",
                     "help_text": "Upload supporting endorsements or identification.",
                     "field_type": "file", "required": False,
                     "allowed_mime_types": ["application/pdf", "image/jpeg", "image/png"],
                     "max_file_size_bytes": 5242880, "options": []},
                ],
            })
            service_id = add(db, m.document_services, service_code=code, is_active=False,
                             current_version_id=None, created_by_user_id=staff["id"])
            version_id = add(db, m.document_service_versions, service_id=service_id, version_number=1,
                             version_status="draft", created_by_user_id=staff["id"],
                             row_version=1, **values(config))
            write_fields(db, version_id, config.requirements)
            audit(db, staff["id"], "service_draft_template_created", "document_service", service_id)
    print("Enabled registrar service-management permission.")
    print("Draft service templates are available for review; none were published.")


if __name__ == "__main__":
    main()
