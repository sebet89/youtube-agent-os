from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    PipelineJobModel,
    ProjectEventModel,
    VideoIdeaModel,
    VideoProjectModel,
    WorkflowRunModel,
    YoutubeChannelConnectionModel,
)
from app.domain.enums import ChannelConnectionStatus, JobStatus


class YoutubeChannelConnectionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_connection(
        self,
        *,
        youtube_channel_id: str,
        channel_title: str,
        oauth_subject: str | None,
        access_token_encrypted: str,
        refresh_token_encrypted: str | None,
        token_expires_at: datetime | None,
        scopes: list[str],
        connection_status: ChannelConnectionStatus,
    ) -> YoutubeChannelConnectionModel:
        query = select(YoutubeChannelConnectionModel).where(
            or_(
                YoutubeChannelConnectionModel.youtube_channel_id == youtube_channel_id,
                YoutubeChannelConnectionModel.oauth_subject == oauth_subject,
            )
        )
        connection = self._session.scalar(query)
        if connection is None:
            connection = YoutubeChannelConnectionModel(
                youtube_channel_id=youtube_channel_id,
                channel_title=channel_title,
            )
            self._session.add(connection)

        connection.channel_title = channel_title
        connection.oauth_subject = oauth_subject
        connection.access_token_encrypted = access_token_encrypted
        connection.refresh_token_encrypted = refresh_token_encrypted
        connection.token_expires_at = token_expires_at
        connection.scopes = scopes
        connection.connection_status = connection_status
        self._session.flush()
        return connection


class VideoProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_project_or_raise(self, project_id: str) -> VideoProjectModel:
        query = (
            select(VideoProjectModel)
            .options(
                joinedload(VideoProjectModel.idea).joinedload(VideoIdeaModel.channel_connection),
                joinedload(VideoProjectModel.analytics_snapshots),
                joinedload(VideoProjectModel.publication_reviews),
                joinedload(VideoProjectModel.media_assets),
                joinedload(VideoProjectModel.project_events),
                joinedload(VideoProjectModel.workflow_runs),
            )
            .where(VideoProjectModel.id == project_id)
        )
        project = self._session.scalar(query)
        if project is None:
            raise ValueError(f"Project '{project_id}' was not found.")
        return project

    def get_channel_connection_for_project(self, project_id: str) -> YoutubeChannelConnectionModel:
        project = self.get_project_or_raise(project_id)
        return project.idea.channel_connection

    def get_latest_workflow_run(
        self,
        project_id: str,
        workflow_name: str,
    ) -> WorkflowRunModel | None:
        query = (
            select(WorkflowRunModel)
            .where(
                WorkflowRunModel.project_id == project_id,
                WorkflowRunModel.workflow_name == workflow_name,
            )
            .order_by(WorkflowRunModel.created_at.desc())
        )
        return self._session.scalar(query)


class ProjectEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_event(
        self,
        *,
        project_id: str,
        event_type: str,
        message: str,
        metadata_json: dict[str, object] | None = None,
    ) -> ProjectEventModel:
        event = ProjectEventModel(
            project_id=project_id,
            event_type=event_type,
            message=message,
            metadata_json=metadata_json or {},
        )
        self._session.add(event)
        self._session.flush()
        return event


class PipelineJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_job(
        self,
        *,
        project_id: str,
        job_type: str,
        queue_name: str,
    ) -> PipelineJobModel:
        job = PipelineJobModel(
            project_id=project_id,
            job_type=job_type,
            queue_name=queue_name,
            status=JobStatus.PENDING,
        )
        self._session.add(job)
        self._session.flush()
        return job

    def get_job_or_raise(self, pipeline_job_id: str) -> PipelineJobModel:
        job = self._session.get(PipelineJobModel, pipeline_job_id)
        if job is None:
            raise ValueError(f"Pipeline job '{pipeline_job_id}' was not found.")
        return job

    def list_jobs_for_project(self, project_id: str) -> list[PipelineJobModel]:
        query = (
            select(PipelineJobModel)
            .where(PipelineJobModel.project_id == project_id)
            .order_by(PipelineJobModel.created_at.desc())
        )
        return list(self._session.scalars(query))

    @staticmethod
    def mark_running(job: PipelineJobModel) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        job.error_message = None

    @staticmethod
    def mark_finished(
        job: PipelineJobModel,
        *,
        status: JobStatus,
        error_message: str | None = None,
    ) -> None:
        job.status = status
        job.finished_at = datetime.now(UTC)
        job.error_message = error_message
