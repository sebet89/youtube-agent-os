"""add project events

Revision ID: 20260416_0004
Revises: 20260416_0003
Create Date: 2026-04-16 12:45:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260416_0004"
down_revision = "20260416_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["video_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_events_project_id", "project_events", ["project_id"])
    op.create_index("ix_project_events_event_type", "project_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_project_events_event_type", table_name="project_events")
    op.drop_index("ix_project_events_project_id", table_name="project_events")
    op.drop_table("project_events")
