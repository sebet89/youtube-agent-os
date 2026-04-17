from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.db.models import WorkflowRunModel
from app.db.repositories import ProjectEventRepository, VideoProjectRepository
from app.domain.enums import JobStatus, VideoIdeaStatus


@dataclass(slots=True)
class GeneratedMetadata:
    title: str
    description: str
    tags: list[str]
    thumbnail_prompt: str


@dataclass(slots=True)
class GeneratedContentBundle:
    briefing: str
    script: str
    metadata: GeneratedMetadata
    production_plan: str
    workflow_name: str
    team_name: str
    agent_names: list[str]


class ContentWorkflowProvider(Protocol):
    def generate(self, *, video_idea: str, title_hint: str) -> GeneratedContentBundle:
        """Generate the content artifacts for a video idea."""


@dataclass(slots=True)
class ContentGenerationResult:
    project_id: str
    workflow_name: str
    team_name: str
    title: str
    idea_status: str


class ContentGenerationService:
    def __init__(self, provider: ContentWorkflowProvider) -> None:
        self._provider = provider

    def generate_for_project(self, session: Session, *, project_id: str) -> ContentGenerationResult:
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)

        workflow_run = WorkflowRunModel(
            project_id=project.id,
            workflow_name="youtube_content_pipeline",
            status=JobStatus.RUNNING,
            input_payload={
                "video_idea_id": project.idea.id,
                "title_hint": project.idea.title,
            },
            started_at=datetime.now(UTC),
        )
        session.add(workflow_run)
        session.flush()

        bundle = self._provider.generate(
            video_idea=project.idea.raw_idea,
            title_hint=project.idea.title,
        )

        project.generated_briefing = bundle.briefing
        project.generated_script = bundle.script
        project.generated_title = bundle.metadata.title
        project.generated_description = bundle.metadata.description
        project.generated_tags = bundle.metadata.tags
        project.thumbnail_prompt = bundle.metadata.thumbnail_prompt
        project.production_plan = bundle.production_plan
        project.idea.status = VideoIdeaStatus.PRODUCTION_READY

        workflow_run.workflow_name = bundle.workflow_name
        workflow_run.status = JobStatus.SUCCEEDED
        workflow_run.output_payload = {
            "team_name": bundle.team_name,
            "agent_names": bundle.agent_names,
            "generated_title": bundle.metadata.title,
        }
        workflow_run.finished_at = datetime.now(UTC)
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="content_generated",
            message="Briefing, roteiro e metadados foram gerados.",
            metadata_json={
                "workflow_name": bundle.workflow_name,
                "team_name": bundle.team_name,
                "generated_title": bundle.metadata.title,
            },
        )

        session.commit()
        session.refresh(project)

        return ContentGenerationResult(
            project_id=project.id,
            workflow_name=bundle.workflow_name,
            team_name=bundle.team_name,
            title=bundle.metadata.title,
            idea_status=project.idea.status.value,
        )
