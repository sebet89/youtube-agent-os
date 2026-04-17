from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import TokenCipher
from app.db.models import (
    MediaAssetModel,
    PublicationReviewModel,
    VideoProjectModel,
    YoutubeChannelConnectionModel,
)
from app.db.repositories import ProjectEventRepository, VideoProjectRepository
from app.domain.entities import VideoProject
from app.domain.enums import ReviewStatus, VideoIdeaStatus, VideoVisibility
from app.domain.exceptions import HumanReviewRequiredError
from app.services.interfaces import (
    PublicationScheduler,
    YoutubeCaptionUploadRequest,
    YoutubePublishContext,
    YoutubePublisher,
    YoutubeThumbnailUploadRequest,
    YoutubeVideoUploadRequest,
)


@dataclass(slots=True)
class ProjectUploadResult:
    project_id: str
    youtube_video_id: str
    visibility: str
    idea_status: str
    thumbnail_uploaded: bool
    captions_uploaded: bool


@dataclass(slots=True)
class ProjectPublishResult:
    project_id: str
    youtube_video_id: str
    visibility: str
    review_status: str
    published_at: datetime


@dataclass(slots=True)
class ProjectScheduleResult:
    project_id: str
    youtube_video_id: str
    review_status: str
    scheduled_publish_at: datetime
    scheduled_task_id: str


@dataclass(slots=True)
class ProjectReviewResult:
    project_id: str
    review_status: str
    reviewer_name: str
    reviewed_at: datetime


@dataclass(slots=True)
class ProjectRejectionResult:
    project_id: str
    review_status: str
    reviewer_name: str
    reviewed_at: datetime


@dataclass(slots=True)
class ProjectUnscheduleResult:
    project_id: str
    review_status: str
    youtube_video_id: str


class YoutubePublishingService:
    def __init__(
        self,
        publisher: YoutubePublisher,
        token_cipher: TokenCipher,
        scheduler: PublicationScheduler | None = None,
    ) -> None:
        self._publisher = publisher
        self._token_cipher = token_cipher
        self._scheduler = scheduler

    def upload_project_video(
        self,
        session: Session,
        *,
        project_id: str,
        file_path: str,
    ) -> ProjectUploadResult:
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)
        connection = repository.get_channel_connection_for_project(project_id)
        publish_request = YoutubeVideoUploadRequest(
            title=project.generated_title or project.idea.title,
            description=project.generated_description or project.idea.raw_idea,
            file_path=file_path,
            tags=project.generated_tags,
        )
        context = self._build_publish_context(connection)
        external_video_id = self._publisher.upload_private_video(
            context=context,
            request=publish_request,
        )
        thumbnail_asset = self._get_selected_asset(project, asset_type="thumbnail")
        caption_asset = self._get_selected_asset(project, asset_type="subtitles_srt")
        thumbnail_uploaded = False
        captions_uploaded = False
        if thumbnail_asset is not None and thumbnail_asset.storage_path is not None:
            self._publisher.upload_thumbnail(
                context=context,
                request=YoutubeThumbnailUploadRequest(
                    external_video_id=external_video_id,
                    file_path=thumbnail_asset.storage_path,
                ),
            )
            thumbnail_asset.metadata_json = {
                **thumbnail_asset.metadata_json,
                "uploaded_to_youtube": True,
                "uploaded_video_id": external_video_id,
                "uploaded_at": datetime.now(UTC).isoformat(),
            }
            thumbnail_uploaded = True
        if caption_asset is not None and caption_asset.storage_path is not None:
            caption_language = str(caption_asset.metadata_json.get("language") or "pt-BR")
            self._publisher.upload_caption(
                context=context,
                request=YoutubeCaptionUploadRequest(
                    external_video_id=external_video_id,
                    file_path=caption_asset.storage_path,
                    language=caption_language,
                    name="Legenda gerada automaticamente",
                ),
            )
            caption_asset.metadata_json = {
                **caption_asset.metadata_json,
                "uploaded_to_youtube": True,
                "uploaded_video_id": external_video_id,
                "uploaded_language": caption_language,
                "uploaded_at": datetime.now(UTC).isoformat(),
            }
            captions_uploaded = True

        project.youtube_video_id = external_video_id
        project.visibility = VideoVisibility.PRIVATE
        project.idea.status = VideoIdeaStatus.UPLOADED
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="youtube_uploaded_private",
            message="Video enviado ao YouTube como private.",
            metadata_json={
                "youtube_video_id": external_video_id,
                "thumbnail_uploaded": thumbnail_uploaded,
                "captions_uploaded": captions_uploaded,
            },
        )
        session.commit()
        session.refresh(project)

        return ProjectUploadResult(
            project_id=project.id,
            youtube_video_id=external_video_id,
            visibility=project.visibility.value,
            idea_status=project.idea.status.value,
            thumbnail_uploaded=thumbnail_uploaded,
            captions_uploaded=captions_uploaded,
        )

    def approve_project_publication(
        self,
        session: Session,
        *,
        project_id: str,
        reviewer_name: str,
        notes: str | None,
    ) -> ProjectReviewResult:
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)

        review = PublicationReviewModel(
            project_id=project.id,
            reviewer_name=reviewer_name,
            status=ReviewStatus.APPROVED,
            notes=notes,
            reviewed_at=datetime.now(UTC),
        )
        session.add(review)
        project.review_status = ReviewStatus.APPROVED
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="review_approved",
            message="Publicacao aprovada por revisao humana.",
            metadata_json={"reviewer_name": reviewer_name, "notes": notes or ""},
        )
        session.commit()
        session.refresh(project)

        return ProjectReviewResult(
            project_id=project.id,
            review_status=project.review_status.value,
            reviewer_name=review.reviewer_name or reviewer_name,
            reviewed_at=review.reviewed_at or datetime.now(UTC),
        )

    def reject_project_publication(
        self,
        session: Session,
        *,
        project_id: str,
        reviewer_name: str,
        notes: str | None,
    ) -> ProjectRejectionResult:
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)

        review = PublicationReviewModel(
            project_id=project.id,
            reviewer_name=reviewer_name,
            status=ReviewStatus.REJECTED,
            notes=notes,
            reviewed_at=datetime.now(UTC),
        )
        session.add(review)
        project.review_status = ReviewStatus.REJECTED
        project.scheduled_publish_at = None
        project.scheduled_publish_task_id = None
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="review_rejected",
            message="Publicacao rejeitada por revisao humana.",
            metadata_json={"reviewer_name": reviewer_name, "notes": notes or ""},
        )
        session.commit()
        session.refresh(project)

        return ProjectRejectionResult(
            project_id=project.id,
            review_status=project.review_status.value,
            reviewer_name=review.reviewer_name or reviewer_name,
            reviewed_at=review.reviewed_at or datetime.now(UTC),
        )

    def publish_project_video(self, session: Session, *, project_id: str) -> ProjectPublishResult:
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)
        connection = repository.get_channel_connection_for_project(project_id)
        self._ensure_publish_allowed(project)
        if project.youtube_video_id is None:
            raise ValueError("Project must be uploaded to YouTube before publication.")

        context = self._build_publish_context(connection)
        self._publisher.publish_video(context=context, external_video_id=project.youtube_video_id)

        domain_project = VideoProject(
            idea_id=project.idea_id,
            visibility=project.visibility,
            review_status=project.review_status,
            generated_title=project.generated_title,
            generated_description=project.generated_description,
            generated_tags=project.generated_tags,
            thumbnail_prompt=project.thumbnail_prompt,
            youtube_video_id=project.youtube_video_id,
            published_at=project.published_at,
        )
        domain_project.publish_publicly()
        project.visibility = domain_project.visibility
        project.published_at = domain_project.published_at
        project.scheduled_publish_at = None
        project.scheduled_publish_task_id = None
        project.idea.status = VideoIdeaStatus.PUBLISHED
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="youtube_published_public",
            message="Video publicado como public.",
            metadata_json={"youtube_video_id": project.youtube_video_id or ""},
        )
        session.commit()
        session.refresh(project)

        return ProjectPublishResult(
            project_id=project.id,
            youtube_video_id=project.youtube_video_id,
            visibility=project.visibility.value,
            review_status=project.review_status.value,
            published_at=project.published_at or datetime.now(UTC),
        )

    def schedule_project_publication(
        self,
        session: Session,
        *,
        project_id: str,
        publish_at: datetime,
    ) -> ProjectScheduleResult:
        if self._scheduler is None:
            raise ValueError("Publication scheduler is not configured.")
        repository = VideoProjectRepository(session)
        project = repository.get_project_or_raise(project_id)
        self._ensure_publish_allowed(project)
        if project.youtube_video_id is None:
            raise ValueError("Project must be uploaded to YouTube before scheduling publication.")
        publish_at_utc = publish_at.astimezone(UTC)
        if publish_at_utc <= datetime.now(UTC):
            raise ValueError("Scheduled publication must be in the future.")
        if project.scheduled_publish_task_id is not None:
            self._scheduler.cancel_publication(
                scheduled_task_id=project.scheduled_publish_task_id,
            )

        scheduled_task_id = self._scheduler.schedule_publication(
            project_id=project_id,
            publish_at=publish_at_utc,
        )
        project.scheduled_publish_at = publish_at_utc
        project.scheduled_publish_task_id = scheduled_task_id
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="publication_scheduled",
            message="Publicacao agendada para uma data futura.",
            metadata_json={
                "scheduled_publish_at": publish_at_utc.isoformat(),
                "scheduled_task_id": scheduled_task_id,
            },
        )
        session.commit()
        session.refresh(project)

        return ProjectScheduleResult(
            project_id=project.id,
            youtube_video_id=project.youtube_video_id or "",
            review_status=project.review_status.value,
            scheduled_publish_at=project.scheduled_publish_at or publish_at_utc,
            scheduled_task_id=scheduled_task_id,
        )

    def cancel_scheduled_publication(
        self,
        session: Session,
        *,
        project_id: str,
    ) -> ProjectUnscheduleResult:
        if self._scheduler is None:
            raise ValueError("Publication scheduler is not configured.")
        project = VideoProjectRepository(session).get_project_or_raise(project_id)
        scheduled_task_id = project.scheduled_publish_task_id
        if scheduled_task_id is None or project.scheduled_publish_at is None:
            raise ValueError("Project has no scheduled publication to cancel.")

        self._scheduler.cancel_publication(scheduled_task_id=scheduled_task_id)
        project.scheduled_publish_at = None
        project.scheduled_publish_task_id = None
        ProjectEventRepository(session).create_event(
            project_id=project.id,
            event_type="publication_unscheduled",
            message="Agendamento de publicacao cancelado.",
            metadata_json={"scheduled_task_id": scheduled_task_id},
        )
        session.commit()
        session.refresh(project)

        return ProjectUnscheduleResult(
            project_id=project.id,
            review_status=project.review_status.value,
            youtube_video_id=project.youtube_video_id or "",
        )

    def execute_scheduled_publication(
        self,
        session: Session,
        *,
        project_id: str,
        task_id: str,
    ) -> ProjectPublishResult:
        project = VideoProjectRepository(session).get_project_or_raise(project_id)
        if project.scheduled_publish_task_id != task_id:
            raise ValueError("Scheduled publication task is stale for this project.")
        scheduled_publish_at = project.scheduled_publish_at
        if scheduled_publish_at is None:
            raise ValueError("Project has no scheduled publication pending.")
        if scheduled_publish_at > datetime.now(UTC):
            raise ValueError("Scheduled publication time has not been reached yet.")
        return self.publish_project_video(session, project_id=project_id)

    def _build_publish_context(
        self,
        connection: YoutubeChannelConnectionModel,
    ) -> YoutubePublishContext:
        access_token_encrypted = connection.access_token_encrypted
        if access_token_encrypted is None:
            raise ValueError("Connected channel is missing an access token.")
        refresh_token_encrypted = connection.refresh_token_encrypted
        return YoutubePublishContext(
            access_token=self._token_cipher.decrypt(access_token_encrypted),
            refresh_token=(
                self._token_cipher.decrypt(refresh_token_encrypted)
                if refresh_token_encrypted is not None
                else None
            ),
            token_expires_at=connection.token_expires_at,
            scopes=list(connection.scopes),
        )

    @staticmethod
    def _ensure_publish_allowed(project: VideoProjectModel) -> None:
        if project.review_status != ReviewStatus.APPROVED:
            raise HumanReviewRequiredError(
                "Project requires human approval before public publication."
            )

    @staticmethod
    def _get_selected_asset(
        project: VideoProjectModel,
        *,
        asset_type: str,
    ) -> MediaAssetModel | None:
        matching_assets = [
            asset for asset in project.media_assets if asset.asset_type == asset_type
        ]
        if asset_type == "thumbnail":
            return next(
                (asset for asset in matching_assets if asset.metadata_json.get("selected") is True),
                matching_assets[0] if matching_assets else None,
            )
        return matching_assets[0] if matching_assets else None
