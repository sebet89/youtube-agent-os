from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from app.db.models import PipelineJobModel
from app.db.repositories import (
    PipelineJobRepository,
    ProjectEventRepository,
    VideoProjectRepository,
)
from app.domain.enums import JobStatus
from app.services.content_generation import ContentGenerationService
from app.services.media_assets import MediaAssetPreparationService
from app.services.rendering import VideoRenderingService


@dataclass(slots=True)
class PipelineDispatchResult:
    pipeline_job_id: str
    celery_task_id: str
    status: str
    queue_name: str


@dataclass(slots=True)
class PipelineJobSummary:
    pipeline_job_id: str
    project_id: str
    job_type: str
    queue_name: str
    status: str
    celery_task_id: str | None
    error_message: str | None


class PipelineTaskDispatcher(Protocol):
    def dispatch_project_pipeline(self, *, pipeline_job_id: str, project_id: str) -> str:
        """Dispatch the project pipeline to background execution."""


class PipelineJobService:
    def __init__(self, dispatcher: PipelineTaskDispatcher) -> None:
        self._dispatcher = dispatcher

    def enqueue_project_pipeline(
        self,
        session: Session,
        *,
        project_id: str,
    ) -> PipelineDispatchResult:
        VideoProjectRepository(session).get_project_or_raise(project_id)
        repository = PipelineJobRepository(session)
        pipeline_job = repository.create_job(
            project_id=project_id,
            job_type="project_pipeline",
            queue_name="pipeline",
        )
        celery_task_id = self._dispatcher.dispatch_project_pipeline(
            pipeline_job_id=pipeline_job.id,
            project_id=project_id,
        )
        pipeline_job.celery_task_id = celery_task_id
        ProjectEventRepository(session).create_event(
            project_id=project_id,
            event_type="pipeline_queued",
            message="Pipeline completo foi enviado para processamento em background.",
            metadata_json={
                "pipeline_job_id": pipeline_job.id,
                "celery_task_id": celery_task_id,
                "queue_name": pipeline_job.queue_name,
            },
        )
        session.commit()
        session.refresh(pipeline_job)

        return PipelineDispatchResult(
            pipeline_job_id=pipeline_job.id,
            celery_task_id=celery_task_id,
            status=pipeline_job.status.value,
            queue_name=pipeline_job.queue_name,
        )

    def list_project_jobs(self, session: Session, *, project_id: str) -> list[PipelineJobSummary]:
        repository = PipelineJobRepository(session)
        jobs = repository.list_jobs_for_project(project_id)
        return [
            PipelineJobSummary(
                pipeline_job_id=job.id,
                project_id=job.project_id,
                job_type=job.job_type,
                queue_name=job.queue_name,
                status=job.status.value,
                celery_task_id=job.celery_task_id,
                error_message=job.error_message,
            )
            for job in jobs
        ]


def execute_project_pipeline(
    session: Session,
    *,
    project_id: str,
    content_service: ContentGenerationService,
    media_service: MediaAssetPreparationService,
    render_service: VideoRenderingService,
) -> dict[str, str]:
    content_service.generate_for_project(session, project_id=project_id)
    media_service.prepare_for_project(session, project_id=project_id)
    render_result = render_service.render_project(session, project_id=project_id)
    return {
        "project_id": project_id,
        "output_path": render_result.output_path,
        "idea_status": render_result.idea_status,
    }


def mark_pipeline_job_running(session: Session, pipeline_job_id: str) -> PipelineJobModel:
    repository = PipelineJobRepository(session)
    job = repository.get_job_or_raise(pipeline_job_id)
    repository.mark_running(job)
    ProjectEventRepository(session).create_event(
        project_id=job.project_id,
        event_type="pipeline_running",
        message="Pipeline em background iniciou a execucao do projeto.",
        metadata_json={
            "pipeline_job_id": job.id,
            "celery_task_id": job.celery_task_id,
        },
    )
    session.commit()
    session.refresh(job)
    return job


def mark_pipeline_job_succeeded(session: Session, pipeline_job_id: str) -> PipelineJobModel:
    repository = PipelineJobRepository(session)
    job = repository.get_job_or_raise(pipeline_job_id)
    repository.mark_finished(job, status=JobStatus.SUCCEEDED)
    ProjectEventRepository(session).create_event(
        project_id=job.project_id,
        event_type="pipeline_succeeded",
        message="Pipeline em background concluiu com sucesso.",
        metadata_json={
            "pipeline_job_id": job.id,
            "celery_task_id": job.celery_task_id,
        },
    )
    session.commit()
    session.refresh(job)
    return job


def mark_pipeline_job_failed(
    session: Session,
    pipeline_job_id: str,
    *,
    error_message: str,
) -> PipelineJobModel:
    repository = PipelineJobRepository(session)
    job = repository.get_job_or_raise(pipeline_job_id)
    repository.mark_finished(
        job,
        status=JobStatus.FAILED,
        error_message=error_message,
    )
    ProjectEventRepository(session).create_event(
        project_id=job.project_id,
        event_type="pipeline_failed",
        message="Pipeline em background falhou e precisa de revisao.",
        metadata_json={
            "pipeline_job_id": job.id,
            "celery_task_id": job.celery_task_id,
            "error_message": error_message,
        },
    )
    session.commit()
    session.refresh(job)
    return job
