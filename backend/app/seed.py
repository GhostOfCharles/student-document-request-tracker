from app.db import SessionLocal, utcnow
from app.config import settings
from app.auth import hasher
from app import models as m
from app.common import one, add, change


def seed(db, password):
    if len(password) < 12 or password.startswith("REPLACE_"):
        raise ValueError(
            "Set SDRT_SEED_PASSWORD to an operator-chosen password of at least 12 characters."
        )
    accounts = []
    for role, email, name, student_number, staff_number in [
        ("student", "student@example.test", "Synthetic Student One", "TEST-001", None),
        ("student", "other@example.test", "Synthetic Student Two", "TEST-002", None),
        (
            "staff",
            "registrar@example.test",
            "Synthetic Registrar",
            None,
            "STAFF-TEST-001",
        ),
    ]:
        existing = one(db, m.users, m.users.c.email == email)
        if existing:
            accounts.append(existing["id"])
            continue
        accounts.append(
            add(
                db,
                m.users,
                role=role,
                email=email,
                full_name=name,
                student_number=student_number,
                staff_number=staff_number,
                password_hash=hasher.hash(password),
                can_manage_services=False,
                is_active=True,
                must_change_password=False,
            )
        )
    staff_id = accounts[2]
    for code, name, pay in [
        ("GOOD_MORAL", "Certificate of Good Moral", False),
        ("ENROLLMENT", "Certificate of Enrollment", True),
    ]:
        if one(db, m.document_services, m.document_services.c.service_code == code):
            continue
        sid = add(
            db,
            m.document_services,
            service_code=code,
            is_active=True,
            created_by_user_id=staff_id,
        )
        vid = add(
            db,
            m.document_service_versions,
            service_id=sid,
            version_number=1,
            name=name,
            description="Controlled Week 13 synthetic document service.",
            category="Certificates",
            eligibility_instructions="Use synthetic information and fictional evidence only.",
            processing_days=3,
            payment_required=pay,
            payment_amount="50.00" if pay else None,
            currency_code="PHP",
            payment_instructions="Upload a fictional test receipt. No money is collected."
            if pay
            else None,
            payment_reference_required=pay,
            payment_receipt_required=pay,
            version_status="draft",
            created_by_user_id=staff_id,
            row_version=1,
        )
        fields = [
            ("purpose", "Purpose of request", "text", True),
            ("category", "Request category", "select", True),
            ("needed_on", "Preferred date", "date", False),
            ("synthetic", "I confirm this is synthetic test data", "checkbox", True),
            ("supporting", "Supporting evidence", "file", pay),
        ]
        for order, (key, label, kind, required) in enumerate(fields, 1):
            fid = add(
                db,
                m.service_requirements,
                service_version_id=vid,
                field_key=key,
                label=label,
                help_text="PDF/JPEG/PNG, up to 5 MiB." if kind == "file" else None,
                field_type=kind,
                is_required=required,
                sort_order=order,
                min_length=3 if kind == "text" else None,
                max_length=200 if kind == "text" else None,
                allowed_mime_types=["application/pdf", "image/jpeg", "image/png"]
                if kind == "file"
                else None,
                max_file_size_bytes=5242880 if kind == "file" else None,
            )
            if kind == "select":
                for i, option in enumerate(("scholarship", "employment"), 1):
                    add(
                        db,
                        m.requirement_options,
                        requirement_id=fid,
                        option_value=option,
                        option_label=option.title(),
                        sort_order=i,
                    )
        change(
            db,
            m.document_service_versions,
            vid,
            version_status="published",
            published_at=utcnow(),
        )
        change(db, m.document_services, sid, current_version_id=vid)
    return accounts


if __name__ == "__main__":
    with SessionLocal.begin() as db:
        seed(db, settings.seed_password)
    print(
        "Seeded two synthetic students, one registrar and two published service versions. No credentials printed."
    )
