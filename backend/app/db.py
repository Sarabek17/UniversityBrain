from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

IS_SQLITE = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    # `timeout`: how long a writer waits for the lock instead of failing
    # ("database is locked"). FastAPI runs sync endpoints in a thread pool, so
    # a slow request (translation = many LLM calls) overlaps with the bell's
    # polling; 30 s is far more than any demo request needs.
    connect_args=({"check_same_thread": False, "timeout": 30.0} if IS_SQLITE else {}),
)

if IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record) -> None:
        """WAL lets readers work while one writer holds the lock — without it
        a background GET blocks the write that finishes a translation."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models so all tables are registered on Base.metadata
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
