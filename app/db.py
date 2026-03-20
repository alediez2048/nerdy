# Ad-Ops-Autopilot — Database setup
from sqlalchemy import create_engine, inspect, text
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


def _repair_campaign_schema() -> None:
    """Backfill campaign schema changes for existing local databases."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "campaigns" not in table_names:
        Base.metadata.tables["campaigns"].create(bind=engine, checkfirst=True)
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

    if "sessions" not in table_names:
        return

    session_columns = {column["name"] for column in inspector.get_columns("sessions")}
    if "campaign_id" in session_columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE sessions ADD COLUMN campaign_id VARCHAR(64)"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_sessions_campaign_id ON sessions (campaign_id)")
        )

        if engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = 'fk_sessions_campaign_id_campaigns'
                        ) THEN
                            ALTER TABLE sessions
                            ADD CONSTRAINT fk_sessions_campaign_id_campaigns
                            FOREIGN KEY (campaign_id) REFERENCES campaigns (campaign_id);
                        END IF;
                    END $$;
                    """
                )
            )


def init_db() -> None:
    """Create tables on startup and repair lightweight schema drift."""
    Base.metadata.create_all(bind=engine)
    _repair_campaign_schema()


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
