"""add scheduled publish fields

Revision ID: 20260416_0003
Revises: 20260416_0002
Create Date: 2026-04-16 12:10:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260416_0003"
down_revision = "20260416_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_projects",
        sa.Column("scheduled_publish_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "video_projects",
        sa.Column("scheduled_publish_task_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("video_projects", "scheduled_publish_task_id")
    op.drop_column("video_projects", "scheduled_publish_at")
