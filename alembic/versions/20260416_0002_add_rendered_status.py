"""add rendered status to video idea enum

Revision ID: 20260416_0002
Revises: 20260416_0001
Create Date: 2026-04-16 03:10:00
"""

from __future__ import annotations

from alembic import op

revision = "20260416_0002"
down_revision = "20260416_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE videoideastatus ADD VALUE IF NOT EXISTS 'RENDERED'")


def downgrade() -> None:
    # PostgreSQL enums cannot easily remove values without a rebuild; keep downgrade as no-op.
    pass
