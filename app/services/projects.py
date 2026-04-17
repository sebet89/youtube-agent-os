from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import VideoIdeaModel, VideoProjectModel, YoutubeChannelConnectionModel
from app.db.repositories import ProjectEventRepository
from app.domain.enums import ChannelConnectionStatus, ReviewStatus, VideoIdeaStatus, VideoVisibility


@dataclass(slots=True)
class ProjectCreationResult:
    project_id: str
    idea_id: str
    connection_id: str
    youtube_channel_id: str
    channel_title: str
    title: str
    raw_idea: str
    idea_status: str
    visibility: str
    review_status: str


class ProjectCreationService:
    def create_project(
        self,
        session: Session,
        *,
        connection_id: str,
        title: str,
        raw_idea: str,
        target_audience: str | None = None,
        business_goal: str | None = None,
    ) -> ProjectCreationResult:
        connection = session.get(YoutubeChannelConnectionModel, connection_id)
        if connection is None:
            raise ValueError(f"Channel connection '{connection_id}' was not found.")
        if connection.connection_status != ChannelConnectionStatus.ACTIVE:
            raise ValueError("Channel connection must be active before creating a project.")

        idea = VideoIdeaModel(
            channel_connection_id=connection.id,
            title=title,
            raw_idea=raw_idea,
            target_audience=target_audience,
            business_goal=business_goal,
            status=VideoIdeaStatus.DRAFT,
        )
        session.add(idea)
        session.flush()

        project = VideoProjectModel(
            idea_id=idea.id,
            visibility=VideoVisibility.PRIVATE,
            review_status=ReviewStatus.PENDING,
        )
        session.add(project)
        session.flush()
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="project_created",
            message="Projeto criado e pronto para iniciar a producao.",
            metadata_json={
                "idea_id": idea.id,
                "connection_id": connection.id,
                "channel_title": connection.channel_title,
            },
        )
        session.commit()
        session.refresh(idea)
        session.refresh(project)

        return ProjectCreationResult(
            project_id=project.id,
            idea_id=idea.id,
            connection_id=connection.id,
            youtube_channel_id=connection.youtube_channel_id,
            channel_title=connection.channel_title,
            title=idea.title,
            raw_idea=idea.raw_idea,
            idea_status=idea.status.value,
            visibility=project.visibility.value,
            review_status=project.review_status.value,
        )
