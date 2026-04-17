"""initial domain schema

Revision ID: 20260416_0001
Revises:
Create Date: 2026-04-16 01:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260416_0001"
down_revision = None
branch_labels = None
depends_on = None


channel_connection_status = sa.Enum(
    "PENDING",
    "ACTIVE",
    "REVOKED",
    name="channelconnectionstatus",
)
video_idea_status = sa.Enum(
    "DRAFT",
    "BRIEFING_READY",
    "SCRIPT_READY",
    "METADATA_READY",
    "PRODUCTION_READY",
    "RENDER_READY",
    "UPLOADED",
    "PUBLISHED",
    name="videoideastatus",
)
video_visibility = sa.Enum("PRIVATE", "PUBLIC", "UNLISTED", name="videovisibility")
review_status = sa.Enum("PENDING", "APPROVED", "REJECTED", name="reviewstatus")
media_asset_status = sa.Enum("PENDING", "READY", "FAILED", name="mediaassetstatus")
job_status = sa.Enum("PENDING", "RUNNING", "SUCCEEDED", "FAILED", name="jobstatus")


def upgrade() -> None:
    op.create_table(
        "youtube_channel_connections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("youtube_channel_id", sa.String(length=255), nullable=False),
        sa.Column("channel_title", sa.String(length=255), nullable=False),
        sa.Column("oauth_subject", sa.String(length=255), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("connection_status", channel_connection_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_youtube_channel_connections")),
        sa.UniqueConstraint(
            "oauth_subject",
            name=op.f("uq_youtube_channel_connections_oauth_subject"),
        ),
        sa.UniqueConstraint(
            "youtube_channel_id",
            name=op.f("uq_youtube_channel_connections_youtube_channel_id"),
        ),
    )
    op.create_index(
        op.f("ix_youtube_channel_connections_youtube_channel_id"),
        "youtube_channel_connections",
        ["youtube_channel_id"],
        unique=False,
    )

    op.create_table(
        "video_ideas",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("channel_connection_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("raw_idea", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.String(length=255), nullable=True),
        sa.Column("business_goal", sa.String(length=255), nullable=True),
        sa.Column("status", video_idea_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["channel_connection_id"],
            ["youtube_channel_connections.id"],
            name=op.f("fk_video_ideas_channel_connection_id_youtube_channel_connections"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_video_ideas")),
    )
    op.create_index(
        op.f("ix_video_ideas_channel_connection_id"),
        "video_ideas",
        ["channel_connection_id"],
    )

    op.create_table(
        "video_projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idea_id", sa.String(length=36), nullable=False),
        sa.Column("generated_briefing", sa.Text(), nullable=True),
        sa.Column("generated_script", sa.Text(), nullable=True),
        sa.Column("generated_title", sa.String(length=255), nullable=True),
        sa.Column("generated_description", sa.Text(), nullable=True),
        sa.Column("generated_tags", sa.JSON(), nullable=False),
        sa.Column("thumbnail_prompt", sa.Text(), nullable=True),
        sa.Column("production_plan", sa.Text(), nullable=True),
        sa.Column("visibility", video_visibility, nullable=False),
        sa.Column("review_status", review_status, nullable=False),
        sa.Column("youtube_video_id", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["idea_id"],
            ["video_ideas.id"],
            name=op.f("fk_video_projects_idea_id_video_ideas"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_video_projects")),
        sa.UniqueConstraint("idea_id", name=op.f("uq_video_projects_idea_id")),
    )
    op.create_index(op.f("ix_video_projects_idea_id"), "video_projects", ["idea_id"])
    op.create_index(
        op.f("ix_video_projects_youtube_video_id"),
        "video_projects",
        ["youtube_video_id"],
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("asset_type", sa.String(length=100), nullable=False),
        sa.Column("source_adapter", sa.String(length=100), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=True),
        sa.Column("status", media_asset_status, nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["video_projects.id"],
            name=op.f("fk_media_assets_project_id_video_projects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
    )
    op.create_index(op.f("ix_media_assets_project_id"), "media_assets", ["project_id"])

    op.create_table(
        "pipeline_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("queue_name", sa.String(length=100), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["video_projects.id"],
            name=op.f("fk_pipeline_jobs_project_id_video_projects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_jobs")),
        sa.UniqueConstraint("celery_task_id", name=op.f("uq_pipeline_jobs_celery_task_id")),
    )
    op.create_index(op.f("ix_pipeline_jobs_project_id"), "pipeline_jobs", ["project_id"])

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_name", sa.String(length=100), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["video_projects.id"],
            name=op.f("fk_workflow_runs_project_id_video_projects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_runs")),
    )
    op.create_index(op.f("ix_workflow_runs_project_id"), "workflow_runs", ["project_id"])

    op.create_table(
        "publication_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_name", sa.String(length=255), nullable=True),
        sa.Column("status", review_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["video_projects.id"],
            name=op.f("fk_publication_reviews_project_id_video_projects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_publication_reviews")),
    )
    op.create_index(
        op.f("ix_publication_reviews_project_id"),
        "publication_reviews",
        ["project_id"],
    )

    op.create_table(
        "analytics_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=255), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("comment_count", sa.Integer(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["video_projects.id"],
            name=op.f("fk_analytics_snapshots_project_id_video_projects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analytics_snapshots")),
    )
    op.create_index(
        op.f("ix_analytics_snapshots_project_id"),
        "analytics_snapshots",
        ["project_id"],
    )
    op.create_index(
        op.f("ix_analytics_snapshots_youtube_video_id"),
        "analytics_snapshots",
        ["youtube_video_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_analytics_snapshots_youtube_video_id"), table_name="analytics_snapshots")
    op.drop_index(op.f("ix_analytics_snapshots_project_id"), table_name="analytics_snapshots")
    op.drop_table("analytics_snapshots")

    op.drop_index(op.f("ix_publication_reviews_project_id"), table_name="publication_reviews")
    op.drop_table("publication_reviews")

    op.drop_index(op.f("ix_workflow_runs_project_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")

    op.drop_index(op.f("ix_pipeline_jobs_project_id"), table_name="pipeline_jobs")
    op.drop_table("pipeline_jobs")

    op.drop_index(op.f("ix_media_assets_project_id"), table_name="media_assets")
    op.drop_table("media_assets")

    op.drop_index(op.f("ix_video_projects_youtube_video_id"), table_name="video_projects")
    op.drop_index(op.f("ix_video_projects_idea_id"), table_name="video_projects")
    op.drop_table("video_projects")

    op.drop_index(op.f("ix_video_ideas_channel_connection_id"), table_name="video_ideas")
    op.drop_table("video_ideas")

    op.drop_index(
        op.f("ix_youtube_channel_connections_youtube_channel_id"),
        table_name="youtube_channel_connections",
    )
    op.drop_table("youtube_channel_connections")

    job_status.drop(op.get_bind(), checkfirst=False)
    media_asset_status.drop(op.get_bind(), checkfirst=False)
    review_status.drop(op.get_bind(), checkfirst=False)
    video_visibility.drop(op.get_bind(), checkfirst=False)
    video_idea_status.drop(op.get_bind(), checkfirst=False)
    channel_connection_status.drop(op.get_bind(), checkfirst=False)
