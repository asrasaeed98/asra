from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from findings_api.config import settings

Base = declarative_base()


@lru_cache
def get_engine():
    connect_args = {}
    url = settings.database_url
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    engine = create_engine(url, connect_args=connect_args)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_pragma(dbapi_conn, _connection_record) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return engine


def get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def _migrate_sqlite(engine) -> None:
    """Add columns to existing SQLite DBs without Alembic."""
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "catalog_resources" not in insp.get_table_names():
        return
    existing = {col["name"] for col in insp.get_columns("catalog_resources")}
    additions = {
        "ingestible": "BOOLEAN NOT NULL DEFAULT 0",
        "ingest_block_reason": "VARCHAR(255)",
        "detected_format": "VARCHAR(32)",
        "probed_at": "DATETIME",
        "row_count_hint": "INTEGER",
    }
    with engine.begin() as conn:
        for name, typedef in additions.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE catalog_resources ADD COLUMN {name} {typedef}"))


def init_db() -> None:
    from findings_api import models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite(engine)
