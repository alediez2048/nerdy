# Ad-Ops-Autopilot — Database setup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base

# Import all models so Base.metadata knows about them
import app.models.user  # noqa: F401
import app.models.session  # noqa: F401
import app.models.curation  # noqa: F401
import app.models.share_token  # noqa: F401
import app.models.campaign  # noqa: F401

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create tables on startup (fallback if Alembic not run)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
