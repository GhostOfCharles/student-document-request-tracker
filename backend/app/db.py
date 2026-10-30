from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.config import settings


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    isolation_level="READ COMMITTED",
    connect_args={"connect_timeout": 5, "read_timeout": 10, "write_timeout": 10},
)


@event.listens_for(engine, "connect")
def bound_database_work(connection, record):
    with connection.cursor() as cursor:
        cursor.execute("SET SESSION innodb_lock_wait_timeout=5")
        cursor.execute("SET SESSION max_execution_time=10000")


SessionLocal = sessionmaker(engine, expire_on_commit=False)


def database():
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
