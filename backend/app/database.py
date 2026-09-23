from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, DeclarativeBase, sessionmaker

from app.config import DATA_DIR, settings


class Base(DeclarativeBase):
    pass


DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _ensure_columns() -> None:
    """Lightweight additive migrations for SQLite (create_all won't ALTER)."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(plays)")).fetchall()
        if not rows:
            return
        columns = {row[1] for row in rows}
        if "album_image_url" not in columns:
            conn.execute(text("ALTER TABLE plays ADD COLUMN album_image_url TEXT"))


def init_db() -> None:
    # Import models so metadata is registered before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
