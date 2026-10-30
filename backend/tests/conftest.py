import os
import sys
import logging
from pathlib import Path
import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
config = dotenv_values(ROOT / ".env")
test_url = os.environ.get("SDRT_TEST_DATABASE_URL") or config.get(
    "SDRT_TEST_DATABASE_URL", ""
)
if not test_url.startswith("mysql+pymysql://") or not make_url(
    test_url
).database.endswith("_test"):
    raise RuntimeError("Tests require a disposable MySQL database ending in _test.")
os.environ["SDRT_DATABASE_URL"] = test_url
os.environ["SDRT_ENVIRONMENT"] = "test"
os.environ["SDRT_PRIVATE_DIR"] = str(ROOT / ".private/test-uploads")

from app.db import engine, SessionLocal
from app import models as m
from app.seed import seed
from app.config import settings
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def independent_rate_limits():
    from app.auth import login_limits

    login_limits.clear()


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import text, inspect
    import json

    m.metadata.drop_all(engine)
    with engine.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS alembic_version"))
    command.upgrade(Config(str(ROOT / "backend/alembic.ini")), "head")
    with SessionLocal.begin() as db:
        seed(db, settings.seed_password)
    inspector = inspect(engine)
    with engine.connect() as c:
        report = {
            "mysql_version": c.scalar(text("SELECT VERSION()")),
            "tables": inspector.get_table_names(),
            "triggers": [r[0] for r in c.execute(text("SHOW TRIGGERS"))],
        }
    report["constraints"] = {
        t: {
            "checks": [v["name"] for v in inspector.get_check_constraints(t)],
            "unique": [v["name"] for v in inspector.get_unique_constraints(t)],
            "foreign_keys": len(inspector.get_foreign_keys(t)),
        }
        for t in m.metadata.tables
    }
    (ROOT / "evidence/week13/verification/mysql-schema.json").write_text(
        json.dumps(report, indent=2)
    )
    handler = logging.FileHandler(
        ROOT / "evidence/week13/logs/automation-tests.jsonl", mode="w", encoding="utf-8"
    )
    logger = logging.getLogger("sdrt.automation")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    print(
        f"MYSQL MIGRATION PASS: {report['mysql_version']}; {len(report['tables'])} tables; {len(report['triggers'])} immutable-history triggers"
    )
    yield
    logger.removeHandler(handler)
    handler.close()


def authenticated(email):
    client = TestClient(app)
    client.headers["origin"] = "http://localhost:8000"
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"login": email, "password": settings.seed_password},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/csrf").json()[
        "csrf_token"
    ]
    return client


@pytest.fixture
def student():
    with authenticated("student@example.test") as client:
        yield client


@pytest.fixture
def other():
    with authenticated("other@example.test") as client:
        yield client


@pytest.fixture
def staff():
    with authenticated("registrar@example.test") as client:
        yield client
