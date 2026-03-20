"""add campaigns table and session campaign_id

Revision ID: 7c8f2f5c9b11
Revises: dfdf9e56fd7a
Create Date: 2026-03-20 21:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c8f2f5c9b11"
down_revision: Union[str, Sequence[str], None] = "dfdf9e56fd7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add campaign schema for existing databases."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "campaigns" not in table_names:
        op.create_table(
            "campaigns",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("campaign_id", sa.String(64), unique=True, index=True, nullable=False),
            sa.Column("name", sa.String(256), nullable=False),
            sa.Column("user_id", sa.String(256), index=True, nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("audience", sa.String(32), nullable=True),
            sa.Column("campaign_goal", sa.String(32), nullable=True),
            sa.Column("default_config", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'active'")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    inspector = sa.inspect(bind)
    session_columns = {column["name"] for column in inspector.get_columns("sessions")}
    if "campaign_id" not in session_columns:
        op.add_column("sessions", sa.Column("campaign_id", sa.String(64), nullable=True))
        op.execute("CREATE INDEX IF NOT EXISTS ix_sessions_campaign_id ON sessions (campaign_id)")

        if bind.dialect.name == "postgresql":
            op.execute(
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


def downgrade() -> None:
    """Remove campaign schema additions."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    session_columns = {column["name"] for column in inspector.get_columns("sessions")}
    if "campaign_id" in session_columns:
        if bind.dialect.name == "postgresql":
            op.execute(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_sessions_campaign_id_campaigns'
                    ) THEN
                        ALTER TABLE sessions DROP CONSTRAINT fk_sessions_campaign_id_campaigns;
                    END IF;
                END $$;
                """
            )
        op.execute("DROP INDEX IF EXISTS ix_sessions_campaign_id")
        op.drop_column("sessions", "campaign_id")

    if "campaigns" in set(inspector.get_table_names()):
        op.drop_table("campaigns")
