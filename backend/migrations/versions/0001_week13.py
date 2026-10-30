"""Week 13 foundations and durable automation, all 23 Chapter 5 core entities."""

from alembic import op
from migrations.schema_week13 import metadata

revision = "0001_week13"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Immutable schema snapshot, independent of future application models.
    metadata.create_all(op.get_bind())
    for table in (
        "request_revisions",
        "request_field_values",
        "request_attachments",
        "payment_reviews",
        "request_status_history",
        "request_notes",
        "audit_logs",
    ):
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Historical evidence is immutable'"
            )
    for action in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER immutable_published_version_{action.lower()} BEFORE {action} ON document_service_versions FOR EACH ROW BEGIN IF OLD.version_status = 'published' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Published service version is immutable'; END IF; END"
        )
        op.execute(
            f"CREATE TRIGGER immutable_published_requirement_{action.lower()} BEFORE {action} ON service_requirements FOR EACH ROW BEGIN IF EXISTS (SELECT 1 FROM document_service_versions WHERE id=OLD.service_version_id AND version_status='published') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Published requirement is immutable'; END IF; END"
        )
        op.execute(
            f"CREATE TRIGGER immutable_published_option_{action.lower()} BEFORE {action} ON requirement_options FOR EACH ROW BEGIN IF EXISTS (SELECT 1 FROM service_requirements r JOIN document_service_versions v ON v.id=r.service_version_id WHERE r.id=OLD.requirement_id AND v.version_status='published') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Published option is immutable'; END IF; END"
        )


def downgrade():
    metadata.drop_all(op.get_bind())
