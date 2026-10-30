"""Prevent adding new requirements/options to an already published version."""

from alembic import op

revision = "0002_published_children"
down_revision = "0001_week13"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TRIGGER immutable_published_requirement_insert BEFORE INSERT ON service_requirements FOR EACH ROW BEGIN IF EXISTS (SELECT 1 FROM document_service_versions WHERE id=NEW.service_version_id AND version_status='published') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Published requirement is immutable'; END IF; END"
    )
    op.execute(
        "CREATE TRIGGER immutable_published_option_insert BEFORE INSERT ON requirement_options FOR EACH ROW BEGIN IF EXISTS (SELECT 1 FROM service_requirements r JOIN document_service_versions v ON v.id=r.service_version_id WHERE r.id=NEW.requirement_id AND v.version_status='published') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Published option is immutable'; END IF; END"
    )


def downgrade():
    op.execute("DROP TRIGGER immutable_published_option_insert")
    op.execute("DROP TRIGGER immutable_published_requirement_insert")
