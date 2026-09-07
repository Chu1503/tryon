from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(
    settings.resolved_database_url,
    connect_args={"check_same_thread": False, "timeout": 30} if settings.resolved_database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if settings.resolved_database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def create_database() -> None:
    from app.models import AppSettings, Garment  # noqa: F401

    Base.metadata.create_all(engine)
    # This local-first app deliberately avoids a migration server dependency.
    # Keep existing SQLite wardrobes compatible as cache metadata evolves.
    if settings.resolved_database_url.startswith("sqlite"):
        inspector = inspect(engine)
        garment_columns = {column["name"] for column in inspector.get_columns("garments")}
        garment_additions = {
            "tryon_front_profile": "VARCHAR(160)",
            "tryon_back_profile": "VARCHAR(160)",
            "tryon_front_cutout_path": "VARCHAR(512)",
            "tryon_back_cutout_path": "VARCHAR(512)",
        }
        settings_columns = {column["name"] for column in inspector.get_columns("app_settings")}
        settings_additions = {
            "display_name": "VARCHAR(80) NOT NULL DEFAULT 'CHU'",
            "body_front_cutout_path": "VARCHAR(512)",
            "body_back_cutout_path": "VARCHAR(512)",
        }
        with engine.begin() as connection:
            for name, sql_type in garment_additions.items():
                if name not in garment_columns:
                    connection.execute(text(f"ALTER TABLE garments ADD COLUMN {name} {sql_type}"))
            for name, sql_type in settings_additions.items():
                if name not in settings_columns:
                    connection.execute(text(f"ALTER TABLE app_settings ADD COLUMN {name} {sql_type}"))


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
