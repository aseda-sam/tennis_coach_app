from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


# Create SQLAlchemy engine
def _engine_kwargs() -> dict:
    """Get engine kwargs based on environment."""
    if "sqlite" in settings.database_url:
        return {"connect_args": {"check_same_thread": False}}
    else:
        return {}


engine = create_engine(
    settings.database_url,
    **_engine_kwargs(),
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


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
