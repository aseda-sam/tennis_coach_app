from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
    pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all database tables."""
    # Import models here to avoid circular imports
    from app.models import video  # noqa: F401

    Base.metadata.create_all(bind=engine)


def create_tables_if_not_exists() -> None:
    """Create tables only if they don't exist (for development convenience)."""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Only create if no tables exist (fresh database)
    if not existing_tables:
        create_tables()
