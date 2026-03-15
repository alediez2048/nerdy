"""initial schema — users, sessions, curated_sets, curated_ads

Revision ID: dfdf9e56fd7a
Revises:
Create Date: 2026-03-15 16:05:02.217932

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dfdf9e56fd7a"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all application tables."""
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("google_id", sa.String(256), unique=True, index=True, nullable=False),
        sa.Column("email", sa.String(256), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("picture_url", sa.String(1024), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("user_id", sa.String(256), index=True, nullable=False),
        sa.Column("config", sa.JSON, default=dict),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("celery_task_id", sa.String(64), nullable=True),
        sa.Column("results_summary", sa.JSON, nullable=True),
        sa.Column("ledger_path", sa.String(512), nullable=True),
        sa.Column("output_path", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Curated sets
    op.create_table(
        "curated_sets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("sessions.id"), index=True, nullable=False),
        sa.Column("name", sa.String(256), default="Default Set"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Curated ads
    op.create_table(
        "curated_ads",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "curated_set_id", sa.Integer, sa.ForeignKey("curated_sets.id"), index=True, nullable=False
        ),
        sa.Column("ad_id", sa.String(64), index=True, nullable=False),
        sa.Column("position", sa.Integer, default=0),
        sa.Column("annotation", sa.Text, nullable=True),
        sa.Column("edited_copy", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop all application tables in reverse order."""
    op.drop_table("curated_ads")
    op.drop_table("curated_sets")
    op.drop_table("sessions")
    op.drop_table("users")
