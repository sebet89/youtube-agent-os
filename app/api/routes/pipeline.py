from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_pipeline_job_service
from app.services.pipeline import PipelineJobService

router = APIRouter(prefix="/projects")


@router.post("/{project_id}/pipeline/queue")
def queue_project_pipeline(
    project_id: str,
    pipeline_service: Annotated[PipelineJobService, Depends(get_pipeline_job_service)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        result = pipeline_service.enqueue_project_pipeline(session, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "pipeline_job_id": result.pipeline_job_id,
        "celery_task_id": result.celery_task_id,
        "status": result.status,
        "queue_name": result.queue_name,
    }


@router.get("/{project_id}/jobs")
def list_project_jobs(
    project_id: str,
    pipeline_service: Annotated[PipelineJobService, Depends(get_pipeline_job_service)],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    jobs = pipeline_service.list_project_jobs(session, project_id=project_id)
    return {
        "project_id": project_id,
        "jobs": [
            {
                "pipeline_job_id": job.pipeline_job_id,
                "job_type": job.job_type,
                "queue_name": job.queue_name,
                "status": job.status,
                "celery_task_id": job.celery_task_id,
                "error_message": job.error_message,
            }
            for job in jobs
        ],
    }
