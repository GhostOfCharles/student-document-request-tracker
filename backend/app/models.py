"""Week 13 schema transcribed from Chapter 5 tables; MySQL only."""

from sqlalchemy import (
    Table,
    Column,
    MetaData,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.mysql import (
    BIGINT,
    INTEGER,
    SMALLINT,
    VARCHAR,
    CHAR,
    BINARY,
    BOOLEAN,
    DATETIME,
    DATE,
    TEXT,
    JSON,
    DECIMAL,
)

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column("role", VARCHAR(20), nullable=False),
    Column("student_number", VARCHAR(50), nullable=True, unique=True),
    Column("staff_number", VARCHAR(50), nullable=True, unique=True),
    Column("full_name", VARCHAR(150), nullable=False),
    Column("email", VARCHAR(254), nullable=False, unique=True),
    Column("password_hash", VARCHAR(255), nullable=False),
    Column("phone_number", VARCHAR(30), nullable=True),
    Column("can_manage_services", BOOLEAN, nullable=False),
    Column("is_active", BOOLEAN, nullable=False),
    Column("must_change_password", BOOLEAN, nullable=False),
    Column("last_login_at", DATETIME(fsp=6), nullable=True),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("updated_at", DATETIME(fsp=6), nullable=False),
    CheckConstraint("role IN ('student','staff')", name="ck_users_0"),
    CheckConstraint("role = 'staff' OR student_number IS NOT NULL", name="ck_users_1"),
    CheckConstraint("can_manage_services = 0 OR role = 'staff'", name="ck_users_2"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)


auth_sessions = Table(
    "auth_sessions",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_auth_sessions_user_id",
        ),
        nullable=False,
    ),
    Column("session_token_hash", BINARY(32), nullable=False, unique=True),
    Column("remember_me", BOOLEAN, nullable=False),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("expires_at", DATETIME(fsp=6), nullable=False),
    Column("last_seen_at", DATETIME(fsp=6), nullable=True),
    Column("revoked_at", DATETIME(fsp=6), nullable=True),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_auth_sessions_user_id", auth_sessions.c.user_id)

document_services = Table(
    "document_services",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column("service_code", VARCHAR(50), nullable=False, unique=True),
    Column("is_active", BOOLEAN, nullable=False),
    Column(
        "current_version_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_service_versions.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=True,
            name="fk_document_services_current_version_id",
        ),
        nullable=True,
    ),
    Column(
        "created_by_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_document_services_created_by_user_id",
        ),
        nullable=False,
    ),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("updated_at", DATETIME(fsp=6), nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_document_services_current_version_id", document_services.c.current_version_id)
Index("ix_document_services_created_by_user_id", document_services.c.created_by_user_id)

document_service_versions = Table(
    "document_service_versions",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "service_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_services.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_document_service_versions_service_id",
        ),
        nullable=False,
    ),
    Column("version_number", INTEGER(unsigned=True), nullable=False),
    Column("name", VARCHAR(150), nullable=False),
    Column("description", TEXT, nullable=True),
    Column("category", VARCHAR(80), nullable=True),
    Column("eligibility_instructions", TEXT, nullable=True),
    Column("processing_days", SMALLINT(unsigned=True), nullable=False),
    Column("payment_required", BOOLEAN, nullable=False),
    Column("payment_amount", DECIMAL(10, 2), nullable=True),
    Column("currency_code", CHAR(3), nullable=False),
    Column("payment_instructions", TEXT, nullable=True),
    Column("payment_reference_required", BOOLEAN, nullable=False),
    Column("payment_receipt_required", BOOLEAN, nullable=False),
    Column("version_status", VARCHAR(20), nullable=False),
    Column(
        "created_by_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_document_service_versions_created_by_user_id",
        ),
        nullable=False,
    ),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("published_at", DATETIME(fsp=6), nullable=True),
    Column("row_version", INTEGER(unsigned=True), nullable=False),
    CheckConstraint(
        "processing_days BETWEEN 1 AND 30", name="ck_document_service_versions_0"
    ),
    CheckConstraint(
        "version_status IN ('draft','published')", name="ck_document_service_versions_1"
    ),
    CheckConstraint(
        "(payment_required = 1 AND payment_amount > 0 AND (payment_reference_required = 1 OR payment_receipt_required = 1)) OR (payment_required = 0 AND payment_amount IS NULL AND payment_reference_required = 0 AND payment_receipt_required = 0)",
        name="ck_document_service_versions_2",
    ),
    UniqueConstraint(
        "service_id", "version_number", name="uq_document_service_versions_0"
    ),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_document_service_versions_service_id", document_service_versions.c.service_id)
Index(
    "ix_document_service_versions_created_by_user_id",
    document_service_versions.c.created_by_user_id,
)

service_requirements = Table(
    "service_requirements",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "service_version_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_service_versions.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_service_requirements_service_version_id",
        ),
        nullable=False,
    ),
    Column("field_key", VARCHAR(80), nullable=False),
    Column("label", VARCHAR(150), nullable=False),
    Column("help_text", TEXT, nullable=True),
    Column("field_type", VARCHAR(20), nullable=False),
    Column("is_required", BOOLEAN, nullable=False),
    Column("sort_order", INTEGER(unsigned=True), nullable=False),
    Column("min_length", INTEGER(unsigned=True), nullable=True),
    Column("max_length", INTEGER(unsigned=True), nullable=True),
    Column("allowed_mime_types", JSON, nullable=True),
    Column("max_file_size_bytes", BIGINT(unsigned=True), nullable=True),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    CheckConstraint(
        "field_type IN ('text','select','date','checkbox','file')",
        name="ck_service_requirements_0",
    ),
    UniqueConstraint(
        "service_version_id", "field_key", name="uq_service_requirements_0"
    ),
    UniqueConstraint(
        "service_version_id", "sort_order", name="uq_service_requirements_1"
    ),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index(
    "ix_service_requirements_service_version_id",
    service_requirements.c.service_version_id,
)

requirement_options = Table(
    "requirement_options",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "requirement_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "service_requirements.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_requirement_options_requirement_id",
        ),
        nullable=False,
    ),
    Column("option_value", VARCHAR(100), nullable=False),
    Column("option_label", VARCHAR(150), nullable=False),
    Column("sort_order", INTEGER(unsigned=True), nullable=False),
    UniqueConstraint("requirement_id", "option_value", name="uq_requirement_options_0"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_requirement_options_requirement_id", requirement_options.c.requirement_id)

document_requests = Table(
    "document_requests",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column("request_number", VARCHAR(40), nullable=False, unique=True),
    Column(
        "student_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_document_requests_student_user_id",
        ),
        nullable=False,
    ),
    Column(
        "service_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_services.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_document_requests_service_id",
        ),
        nullable=False,
    ),
    Column(
        "service_version_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_service_versions.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_document_requests_service_version_id",
        ),
        nullable=False,
    ),
    Column("status", VARCHAR(32), nullable=False),
    Column("current_revision_number", INTEGER(unsigned=True), nullable=False),
    Column("row_version", INTEGER(unsigned=True), nullable=False),
    Column("submitted_at", DATETIME(fsp=6), nullable=True),
    Column("due_at", DATETIME(fsp=6), nullable=True),
    Column("last_progress_at", DATETIME(fsp=6), nullable=True),
    Column("released_at", DATETIME(fsp=6), nullable=True),
    Column(
        "released_by_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_document_requests_released_by_user_id",
        ),
        nullable=True,
    ),
    Column("acknowledged_at", DATETIME(fsp=6), nullable=True),
    Column("closed_at", DATETIME(fsp=6), nullable=True),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("updated_at", DATETIME(fsp=6), nullable=False),
    Column("client_submission_key", VARCHAR(64), nullable=True, unique=True),
    Column("submission_payload_hash", BINARY(32), nullable=True),
    CheckConstraint(
        "status IN ('submitted','under_review','needs_correction','processing','ready_for_release','released','completed','rejected','cancelled')",
        name="ck_document_requests_0",
    ),
    CheckConstraint("row_version > 0", name="ck_document_requests_1"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_document_requests_student_user_id", document_requests.c.student_user_id)
Index("ix_document_requests_service_id", document_requests.c.service_id)
Index("ix_document_requests_service_version_id", document_requests.c.service_version_id)
Index(
    "ix_document_requests_released_by_user_id", document_requests.c.released_by_user_id
)

request_revisions = Table(
    "request_revisions",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "request_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_requests.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_revisions_request_id",
        ),
        nullable=False,
    ),
    Column("revision_number", INTEGER(unsigned=True), nullable=False),
    Column("revision_type", VARCHAR(20), nullable=False),
    Column("revision_status", VARCHAR(20), nullable=False),
    Column("payment_reference", VARCHAR(120), nullable=True),
    Column(
        "payment_receipt_file_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "stored_files.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_revisions_payment_receipt_file_id",
        ),
        nullable=True,
    ),
    Column(
        "submitted_by_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_revisions_submitted_by_user_id",
        ),
        nullable=True,
    ),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("submitted_at", DATETIME(fsp=6), nullable=True),
    Column("client_submission_key", VARCHAR(64), nullable=True, unique=True),
    Column("submission_payload_hash", BINARY(32), nullable=True),
    CheckConstraint(
        "revision_type IN ('initial','correction')", name="ck_request_revisions_0"
    ),
    CheckConstraint("revision_status = 'submitted'", name="ck_request_revisions_1"),
    UniqueConstraint("request_id", "revision_number", name="uq_request_revisions_0"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_request_revisions_request_id", request_revisions.c.request_id)
Index(
    "ix_request_revisions_payment_receipt_file_id",
    request_revisions.c.payment_receipt_file_id,
)
Index(
    "ix_request_revisions_submitted_by_user_id",
    request_revisions.c.submitted_by_user_id,
)

request_field_values = Table(
    "request_field_values",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "revision_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "request_revisions.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_field_values_revision_id",
        ),
        nullable=False,
    ),
    Column(
        "requirement_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "service_requirements.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_field_values_requirement_id",
        ),
        nullable=False,
    ),
    Column("text_value", TEXT, nullable=True),
    Column("date_value", DATE, nullable=True),
    Column("boolean_value", BOOLEAN, nullable=True),
    Column(
        "selected_option_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "requirement_options.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_field_values_selected_option_id",
        ),
        nullable=True,
    ),
    CheckConstraint(
        "(text_value IS NOT NULL) + (date_value IS NOT NULL) + (boolean_value IS NOT NULL) + (selected_option_id IS NOT NULL) = 1",
        name="ck_request_field_values_0",
    ),
    UniqueConstraint("revision_id", "requirement_id", name="uq_request_field_values_0"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_request_field_values_revision_id", request_field_values.c.revision_id)
Index("ix_request_field_values_requirement_id", request_field_values.c.requirement_id)
Index(
    "ix_request_field_values_selected_option_id",
    request_field_values.c.selected_option_id,
)

stored_files = Table(
    "stored_files",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "uploaded_by_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_stored_files_uploaded_by_user_id",
        ),
        nullable=False,
    ),
    Column("original_filename", VARCHAR(255), nullable=False),
    Column("storage_key", VARCHAR(500), nullable=False, unique=True),
    Column("mime_type", VARCHAR(100), nullable=False),
    Column("size_bytes", BIGINT(unsigned=True), nullable=False),
    Column("sha256_hex", CHAR(64), nullable=False),
    Column("storage_status", VARCHAR(20), nullable=False),
    Column("staging_expires_at", DATETIME(fsp=6), nullable=True),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("verified_at", DATETIME(fsp=6), nullable=True),
    CheckConstraint(
        "storage_status IN ('staging','ready','removed')", name="ck_stored_files_0"
    ),
    CheckConstraint("size_bytes BETWEEN 1 AND 5242880", name="ck_stored_files_1"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_stored_files_uploaded_by_user_id", stored_files.c.uploaded_by_user_id)

request_attachments = Table(
    "request_attachments",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "revision_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "request_revisions.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_attachments_revision_id",
        ),
        nullable=False,
    ),
    Column(
        "requirement_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "service_requirements.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_attachments_requirement_id",
        ),
        nullable=False,
    ),
    Column(
        "stored_file_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "stored_files.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_attachments_stored_file_id",
        ),
        nullable=False,
    ),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    UniqueConstraint("revision_id", "requirement_id", name="uq_request_attachments_0"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_request_attachments_revision_id", request_attachments.c.revision_id)
Index("ix_request_attachments_requirement_id", request_attachments.c.requirement_id)
Index("ix_request_attachments_stored_file_id", request_attachments.c.stored_file_id)

payment_reviews = Table(
    "payment_reviews",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "revision_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "request_revisions.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_payment_reviews_revision_id",
        ),
        nullable=False,
    ),
    Column(
        "reviewed_by_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_payment_reviews_reviewed_by_user_id",
        ),
        nullable=False,
    ),
    Column("outcome", VARCHAR(25), nullable=False),
    Column("review_note", TEXT, nullable=True),
    Column("reviewed_at", DATETIME(fsp=6), nullable=False),
    CheckConstraint(
        "outcome IN ('verified','needs_correction','rejected')",
        name="ck_payment_reviews_0",
    ),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_payment_reviews_revision_id", payment_reviews.c.revision_id)
Index("ix_payment_reviews_reviewed_by_user_id", payment_reviews.c.reviewed_by_user_id)

correction_rounds = Table(
    "correction_rounds",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "request_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_requests.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_correction_rounds_request_id",
        ),
        nullable=False,
    ),
    Column("round_number", INTEGER(unsigned=True), nullable=False),
    Column(
        "source_revision_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "request_revisions.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_correction_rounds_source_revision_id",
        ),
        nullable=False,
    ),
    Column(
        "issued_by_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_correction_rounds_issued_by_user_id",
        ),
        nullable=False,
    ),
    Column("general_instructions", TEXT, nullable=False),
    Column("issued_at", DATETIME(fsp=6), nullable=False),
    Column(
        "resolved_revision_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "request_revisions.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_correction_rounds_resolved_revision_id",
        ),
        nullable=True,
    ),
    Column("resolved_at", DATETIME(fsp=6), nullable=True),
    CheckConstraint(
        "(resolved_revision_id IS NULL) = (resolved_at IS NULL)",
        name="ck_correction_rounds_0",
    ),
    UniqueConstraint("request_id", "round_number", name="uq_correction_rounds_0"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_correction_rounds_request_id", correction_rounds.c.request_id)
Index("ix_correction_rounds_source_revision_id", correction_rounds.c.source_revision_id)
Index("ix_correction_rounds_issued_by_user_id", correction_rounds.c.issued_by_user_id)
Index(
    "ix_correction_rounds_resolved_revision_id",
    correction_rounds.c.resolved_revision_id,
)

correction_items = Table(
    "correction_items",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "correction_round_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "correction_rounds.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_correction_items_correction_round_id",
        ),
        nullable=False,
    ),
    Column("target_kind", VARCHAR(30), nullable=False),
    Column(
        "requirement_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "service_requirements.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_correction_items_requirement_id",
        ),
        nullable=True,
    ),
    Column("instruction", TEXT, nullable=False),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    CheckConstraint(
        "target_kind IN ('requirement','payment_reference','payment_receipt')",
        name="ck_correction_items_0",
    ),
    CheckConstraint(
        "(target_kind = 'requirement' AND requirement_id IS NOT NULL) OR (target_kind <> 'requirement' AND requirement_id IS NULL)",
        name="ck_correction_items_1",
    ),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_correction_items_correction_round_id", correction_items.c.correction_round_id)
Index("ix_correction_items_requirement_id", correction_items.c.requirement_id)

request_status_history = Table(
    "request_status_history",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "request_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_requests.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_status_history_request_id",
        ),
        nullable=False,
    ),
    Column(
        "revision_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "request_revisions.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_status_history_revision_id",
        ),
        nullable=True,
    ),
    Column("previous_status", VARCHAR(32), nullable=True),
    Column("new_status", VARCHAR(32), nullable=False),
    Column(
        "changed_by_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_status_history_changed_by_user_id",
        ),
        nullable=True,
    ),
    Column("change_source", VARCHAR(20), nullable=False),
    Column("public_remarks", TEXT, nullable=True),
    Column("internal_remarks", TEXT, nullable=True),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_request_status_history_request_id", request_status_history.c.request_id)
Index("ix_request_status_history_revision_id", request_status_history.c.revision_id)
Index(
    "ix_request_status_history_changed_by_user_id",
    request_status_history.c.changed_by_user_id,
)

request_notes = Table(
    "request_notes",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "request_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_requests.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_notes_request_id",
        ),
        nullable=False,
    ),
    Column(
        "author_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_notes_author_user_id",
        ),
        nullable=False,
    ),
    Column("visibility", VARCHAR(20), nullable=False),
    Column("note_body", TEXT, nullable=False),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    CheckConstraint(
        "visibility IN ('staff_only','student_visible')", name="ck_request_notes_0"
    ),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_request_notes_request_id", request_notes.c.request_id)
Index("ix_request_notes_author_user_id", request_notes.c.author_user_id)

notifications = Table(
    "notifications",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "recipient_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_notifications_recipient_user_id",
        ),
        nullable=False,
    ),
    Column("notification_type", VARCHAR(50), nullable=False),
    Column(
        "request_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_requests.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_notifications_request_id",
        ),
        nullable=True,
    ),
    Column(
        "service_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_services.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_notifications_service_id",
        ),
        nullable=True,
    ),
    Column(
        "automation_job_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "automation_jobs.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_notifications_automation_job_id",
        ),
        nullable=True,
    ),
    Column("event_key", VARCHAR(191), nullable=False),
    Column("title", VARCHAR(180), nullable=False),
    Column("message", TEXT, nullable=False),
    Column("read_at", DATETIME(fsp=6), nullable=True),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    UniqueConstraint("recipient_user_id", "event_key", name="uq_notifications_0"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_notifications_recipient_user_id", notifications.c.recipient_user_id)
Index("ix_notifications_request_id", notifications.c.request_id)
Index("ix_notifications_service_id", notifications.c.service_id)
Index("ix_notifications_automation_job_id", notifications.c.automation_job_id)

automation_runs = Table(
    "automation_runs",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column("job_name", VARCHAR(80), nullable=False),
    Column("trigger_type", VARCHAR(20), nullable=False),
    Column("scheduled_for", DATETIME(fsp=6), nullable=True),
    Column("started_at", DATETIME(fsp=6), nullable=False),
    Column("finished_at", DATETIME(fsp=6), nullable=True),
    Column("status", VARCHAR(25), nullable=False),
    Column("records_scanned", INTEGER(unsigned=True), nullable=False),
    Column("tasks_created", INTEGER(unsigned=True), nullable=False),
    Column("error_code", VARCHAR(80), nullable=True),
    Column("error_summary", TEXT, nullable=True),
    CheckConstraint(
        "status IN ('running','succeeded','failed')", name="ck_automation_runs_0"
    ),
    CheckConstraint(
        "trigger_type IN ('scheduled','manual')", name="ck_automation_runs_1"
    ),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)


automation_jobs = Table(
    "automation_jobs",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "automation_run_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "automation_runs.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_automation_jobs_automation_run_id",
        ),
        nullable=True,
    ),
    Column("job_type", VARCHAR(60), nullable=False),
    Column(
        "request_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_requests.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_automation_jobs_request_id",
        ),
        nullable=True,
    ),
    Column(
        "recipient_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_automation_jobs_recipient_user_id",
        ),
        nullable=True,
    ),
    Column("idempotency_key", VARCHAR(191), nullable=False, unique=True),
    Column("payload_json", JSON, nullable=True),
    Column("status", VARCHAR(25), nullable=False),
    Column("attempt_count", SMALLINT(unsigned=True), nullable=False),
    Column("max_attempts", SMALLINT(unsigned=True), nullable=False),
    Column("next_attempt_at", DATETIME(fsp=6), nullable=False),
    Column("locked_by", VARCHAR(100), nullable=True),
    Column("locked_until", DATETIME(fsp=6), nullable=True),
    Column("last_error_code", VARCHAR(80), nullable=True),
    Column("last_error_summary", TEXT, nullable=True),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("updated_at", DATETIME(fsp=6), nullable=False),
    Column("completed_at", DATETIME(fsp=6), nullable=True),
    Column(
        "resolved_by_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_automation_jobs_resolved_by_user_id",
        ),
        nullable=True,
    ),
    Column("resolved_at", DATETIME(fsp=6), nullable=True),
    Column("resolution_note", TEXT, nullable=True),
    CheckConstraint(
        "status IN ('pending','running','succeeded','failed_permanently','resolved_manually')",
        name="ck_automation_jobs_0",
    ),
    CheckConstraint(
        "attempt_count <= max_attempts AND max_attempts IN (3,6,9)",
        name="ck_automation_jobs_1",
    ),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_automation_jobs_automation_run_id", automation_jobs.c.automation_run_id)
Index("ix_automation_jobs_request_id", automation_jobs.c.request_id)
Index("ix_automation_jobs_recipient_user_id", automation_jobs.c.recipient_user_id)
Index("ix_automation_jobs_resolved_by_user_id", automation_jobs.c.resolved_by_user_id)

automation_attempts = Table(
    "automation_attempts",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "automation_job_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "automation_jobs.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_automation_attempts_automation_job_id",
        ),
        nullable=False,
    ),
    Column("attempt_number", SMALLINT(unsigned=True), nullable=False),
    Column("worker_identifier", VARCHAR(100), nullable=True),
    Column("started_at", DATETIME(fsp=6), nullable=False),
    Column("finished_at", DATETIME(fsp=6), nullable=True),
    Column("outcome", VARCHAR(25), nullable=False),
    Column("error_code", VARCHAR(80), nullable=True),
    Column("error_summary", TEXT, nullable=True),
    Column("duration_ms", INTEGER(unsigned=True), nullable=True),
    CheckConstraint(
        "outcome IN ('running','succeeded','transient_failure','permanent_failure','interrupted')",
        name="ck_automation_attempts_0",
    ),
    UniqueConstraint(
        "automation_job_id", "attempt_number", name="uq_automation_attempts_0"
    ),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index(
    "ix_automation_attempts_automation_job_id", automation_attempts.c.automation_job_id
)

request_alerts = Table(
    "request_alerts",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "request_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_requests.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_alerts_request_id",
        ),
        nullable=False,
    ),
    Column(
        "automation_job_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "automation_jobs.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_request_alerts_automation_job_id",
        ),
        nullable=True,
    ),
    Column("alert_type", VARCHAR(25), nullable=False),
    Column("idempotency_key", VARCHAR(191), nullable=False, unique=True),
    Column("request_status_at_trigger", VARCHAR(32), nullable=False),
    Column("triggered_at", DATETIME(fsp=6), nullable=False),
    Column("resolved_at", DATETIME(fsp=6), nullable=True),
    CheckConstraint("alert_type IN ('aging','escalation')", name="ck_request_alerts_0"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_request_alerts_request_id", request_alerts.c.request_id)
Index("ix_request_alerts_automation_job_id", request_alerts.c.automation_job_id)

daily_request_summaries = Table(
    "daily_request_summaries",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column("summary_date", DATE, nullable=False, unique=True),
    Column("timezone_name", VARCHAR(64), nullable=False),
    Column("submitted_count", INTEGER(unsigned=True), nullable=False),
    Column("under_review_count", INTEGER(unsigned=True), nullable=False),
    Column("needs_correction_count", INTEGER(unsigned=True), nullable=False),
    Column("processing_count", INTEGER(unsigned=True), nullable=False),
    Column("ready_for_release_count", INTEGER(unsigned=True), nullable=False),
    Column("released_count", INTEGER(unsigned=True), nullable=False),
    Column("pending_total", INTEGER(unsigned=True), nullable=False),
    Column("completed_today_count", INTEGER(unsigned=True), nullable=False),
    Column("rejected_today_count", INTEGER(unsigned=True), nullable=False),
    Column("cancelled_today_count", INTEGER(unsigned=True), nullable=False),
    Column("aging_count", INTEGER(unsigned=True), nullable=False),
    Column("escalated_count", INTEGER(unsigned=True), nullable=False),
    Column(
        "automation_run_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "automation_runs.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_daily_request_summaries_automation_run_id",
        ),
        nullable=True,
    ),
    Column("generated_at", DATETIME(fsp=6), nullable=False),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index(
    "ix_daily_request_summaries_automation_run_id",
    daily_request_summaries.c.automation_run_id,
)

audit_logs = Table(
    "audit_logs",
    metadata,
    Column("id", BIGINT(unsigned=True), primary_key=True, autoincrement=True),
    Column(
        "actor_user_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_audit_logs_actor_user_id",
        ),
        nullable=True,
    ),
    Column("action", VARCHAR(100), nullable=False),
    Column("target_type", VARCHAR(60), nullable=False),
    Column("target_id", BIGINT(unsigned=True), nullable=True),
    Column(
        "request_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_requests.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_audit_logs_request_id",
        ),
        nullable=True,
    ),
    Column(
        "service_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "document_services.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_audit_logs_service_id",
        ),
        nullable=True,
    ),
    Column(
        "automation_job_id",
        BIGINT(unsigned=True),
        ForeignKey(
            "automation_jobs.id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            use_alter=False,
            name="fk_audit_logs_automation_job_id",
        ),
        nullable=True,
    ),
    Column("result", VARCHAR(20), nullable=False),
    Column("details_json", JSON, nullable=True),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    CheckConstraint("result IN ('success','failure','denied')", name="ck_audit_logs_0"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)

Index("ix_audit_logs_actor_user_id", audit_logs.c.actor_user_id)
Index("ix_audit_logs_request_id", audit_logs.c.request_id)
Index("ix_audit_logs_service_id", audit_logs.c.service_id)
Index("ix_audit_logs_automation_job_id", audit_logs.c.automation_job_id)

Index(
    "ix_document_requests_student_user_id_created_at",
    document_requests.c.student_user_id,
    document_requests.c.created_at,
)
Index(
    "ix_document_requests_status_due_at",
    document_requests.c.status,
    document_requests.c.due_at,
)
Index(
    "ix_document_requests_status_submitted_at",
    document_requests.c.status,
    document_requests.c.submitted_at,
)
Index(
    "ix_document_requests_service_id_status",
    document_requests.c.service_id,
    document_requests.c.status,
)
Index(
    "ix_automation_jobs_status_next_attempt_at",
    automation_jobs.c.status,
    automation_jobs.c.next_attempt_at,
)
Index(
    "ix_automation_jobs_status_locked_until",
    automation_jobs.c.status,
    automation_jobs.c.locked_until,
)
Index(
    "ix_notifications_recipient_user_id_read_at_created_at",
    notifications.c.recipient_user_id,
    notifications.c.read_at,
    notifications.c.created_at,
)
Index(
    "ix_request_alerts_request_id_alert_type_resolved_at",
    request_alerts.c.request_id,
    request_alerts.c.alert_type,
    request_alerts.c.resolved_at,
)
Index(
    "ix_payment_reviews_revision_id_reviewed_at_id",
    payment_reviews.c.revision_id,
    payment_reviews.c.reviewed_at,
    payment_reviews.c.id,
)
Index(
    "ix_correction_rounds_request_id_resolved_at",
    correction_rounds.c.request_id,
    correction_rounds.c.resolved_at,
)
Index(
    "ix_request_status_history_request_id_created_at",
    request_status_history.c.request_id,
    request_status_history.c.created_at,
)
Index(
    "ix_request_notes_request_id_created_at",
    request_notes.c.request_id,
    request_notes.c.created_at,
)
Index(
    "ix_stored_files_uploaded_by_user_id_storage_status_created_at",
    stored_files.c.uploaded_by_user_id,
    stored_files.c.storage_status,
    stored_files.c.created_at,
)
Index(
    "ix_audit_logs_actor_user_id_created_at",
    audit_logs.c.actor_user_id,
    audit_logs.c.created_at,
)
Index(
    "ix_audit_logs_request_id_created_at",
    audit_logs.c.request_id,
    audit_logs.c.created_at,
)
