from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ProjectEventModel, PublicationReviewModel, VideoProjectModel
from app.domain.enums import ReviewStatus, VideoIdeaStatus, VideoVisibility
from tests.conftest import FakePublicationScheduler, FakeYoutubePublisher


def test_upload_project_to_youtube_keeps_visibility_private(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
    fake_youtube_publisher: FakeYoutubePublisher,
) -> None:
    assert client.post(f"/api/v1/projects/{sample_project_id}/content/generate").status_code == 200
    assert client.post(f"/api/v1/projects/{sample_project_id}/assets/prepare").status_code == 200

    response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/upload",
        json={"file_path": "C:/videos/output.mp4"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["youtube_video_id"] == "yt-uploaded-1"
    assert payload["visibility"] == "private"
    assert payload["idea_status"] == "uploaded"
    assert payload["thumbnail_uploaded"] is True
    assert payload["captions_uploaded"] is True

    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.youtube_video_id == "yt-uploaded-1"
    assert project.visibility == VideoVisibility.PRIVATE
    assert project.idea.status == VideoIdeaStatus.UPLOADED
    assert len(fake_youtube_publisher.thumbnail_uploads) == 1
    assert len(fake_youtube_publisher.caption_uploads) == 1
    thumbnail_assets = [
        asset for asset in project.media_assets if asset.asset_type == "thumbnail"
    ]
    selected_thumbnail = next(
        asset for asset in thumbnail_assets if asset.metadata_json["selected"] is True
    )
    subtitle_asset = next(
        asset for asset in project.media_assets if asset.asset_type == "subtitles_srt"
    )
    assert selected_thumbnail.metadata_json["uploaded_to_youtube"] is True
    assert subtitle_asset.metadata_json["uploaded_to_youtube"] is True
    assert subtitle_asset.metadata_json["uploaded_language"] == "pt-BR"
    upload_events = db_session.scalars(
        select(ProjectEventModel).where(ProjectEventModel.project_id == sample_project_id)
    ).all()
    assert any(event.event_type == "youtube_uploaded_private" for event in upload_events)


def test_upload_project_to_youtube_without_assets_skips_thumbnail_and_captions(
    client: TestClient,
    fake_youtube_publisher: FakeYoutubePublisher,
    sample_project_id: str,
) -> None:
    response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/upload",
        json={"file_path": "C:/videos/output.mp4"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["thumbnail_uploaded"] is False
    assert payload["captions_uploaded"] is False
    assert fake_youtube_publisher.thumbnail_uploads == []
    assert fake_youtube_publisher.caption_uploads == []


def test_publish_project_requires_human_approval(
    client: TestClient,
    sample_project_id: str,
) -> None:
    upload_response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/upload",
        json={"file_path": "C:/videos/output.mp4"},
    )
    assert upload_response.status_code == 200

    publish_response = client.post(f"/api/v1/projects/{sample_project_id}/youtube/publish")

    assert publish_response.status_code == 409
    assert publish_response.json()["detail"] == (
        "Project requires human approval before public publication."
    )


def test_approve_then_publish_project_to_public(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    upload_response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/upload",
        json={"file_path": "C:/videos/output.mp4"},
    )
    assert upload_response.status_code == 200

    approve_response = client.post(
        f"/api/v1/projects/{sample_project_id}/review/approve",
        json={"reviewer_name": "human-reviewer", "notes": "Pode publicar"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["review_status"] == "approved"

    publish_response = client.post(f"/api/v1/projects/{sample_project_id}/youtube/publish")

    assert publish_response.status_code == 200
    payload = publish_response.json()
    assert payload["visibility"] == "public"
    assert payload["review_status"] == "approved"

    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.visibility == VideoVisibility.PUBLIC
    assert project.review_status == ReviewStatus.APPROVED
    assert project.idea.status == VideoIdeaStatus.PUBLISHED
    assert project.published_at is not None

    reviews = db_session.scalars(
        select(PublicationReviewModel).where(PublicationReviewModel.project_id == sample_project_id)
    ).all()
    assert len(reviews) == 1
    assert reviews[0].status == ReviewStatus.APPROVED
    events = db_session.scalars(
        select(ProjectEventModel).where(ProjectEventModel.project_id == sample_project_id)
    ).all()
    event_types = {event.event_type for event in events}
    assert "review_approved" in event_types
    assert "youtube_published_public" in event_types


def test_schedule_project_publication_persists_future_publish(
    client: TestClient,
    db_session: Session,
    fake_publication_scheduler: FakePublicationScheduler,
    sample_project_id: str,
) -> None:
    assert (
        client.post(
            f"/api/v1/projects/{sample_project_id}/youtube/upload",
            json={"file_path": "C:/videos/output.mp4"},
        ).status_code
        == 200
    )
    assert client.post(
        f"/api/v1/projects/{sample_project_id}/review/approve",
        json={"reviewer_name": "human-reviewer", "notes": "Agendar"},
    ).status_code == 200
    publish_at = datetime.now(UTC) + timedelta(hours=2)

    response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/schedule",
        json={"publish_at": publish_at.isoformat()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduled_task_id"] == f"scheduled-{sample_project_id}"
    assert fake_publication_scheduler.scheduled_requests[0][0] == sample_project_id
    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.scheduled_publish_task_id == f"scheduled-{sample_project_id}"
    assert project.scheduled_publish_at is not None
    events = db_session.scalars(
        select(ProjectEventModel).where(ProjectEventModel.project_id == sample_project_id)
    ).all()
    assert any(event.event_type == "publication_scheduled" for event in events)


def test_reschedule_project_publication_cancels_previous_task(
    client: TestClient,
    db_session: Session,
    fake_publication_scheduler: FakePublicationScheduler,
    sample_project_id: str,
) -> None:
    assert (
        client.post(
            f"/api/v1/projects/{sample_project_id}/youtube/upload",
            json={"file_path": "C:/videos/output.mp4"},
        ).status_code
        == 200
    )
    assert client.post(
        f"/api/v1/projects/{sample_project_id}/review/approve",
        json={"reviewer_name": "human-reviewer", "notes": "Agendar"},
    ).status_code == 200
    first_publish_at = datetime.now(UTC) + timedelta(hours=2)
    second_publish_at = datetime.now(UTC) + timedelta(hours=4)

    assert client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/schedule",
        json={"publish_at": first_publish_at.isoformat()},
    ).status_code == 200
    response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/schedule",
        json={"publish_at": second_publish_at.isoformat()},
    )

    assert response.status_code == 200
    assert fake_publication_scheduler.cancelled_task_ids == [f"scheduled-{sample_project_id}"]
    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.scheduled_publish_task_id == f"scheduled-{sample_project_id}"


def test_cancel_scheduled_project_publication_clears_schedule(
    client: TestClient,
    db_session: Session,
    fake_publication_scheduler: FakePublicationScheduler,
    sample_project_id: str,
) -> None:
    assert (
        client.post(
            f"/api/v1/projects/{sample_project_id}/youtube/upload",
            json={"file_path": "C:/videos/output.mp4"},
        ).status_code
        == 200
    )
    assert client.post(
        f"/api/v1/projects/{sample_project_id}/review/approve",
        json={"reviewer_name": "human-reviewer", "notes": "Agendar"},
    ).status_code == 200
    assert client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/schedule",
        json={"publish_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat()},
    ).status_code == 200

    response = client.post(f"/api/v1/projects/{sample_project_id}/youtube/schedule/cancel")

    assert response.status_code == 200
    assert fake_publication_scheduler.cancelled_task_ids[-1] == f"scheduled-{sample_project_id}"
    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.scheduled_publish_at is None
    assert project.scheduled_publish_task_id is None
    events = db_session.scalars(
        select(ProjectEventModel).where(ProjectEventModel.project_id == sample_project_id)
    ).all()
    assert any(event.event_type == "publication_unscheduled" for event in events)


def test_schedule_project_requires_human_approval(
    client: TestClient,
    sample_project_id: str,
) -> None:
    assert (
        client.post(
            f"/api/v1/projects/{sample_project_id}/youtube/upload",
            json={"file_path": "C:/videos/output.mp4"},
        ).status_code
        == 200
    )

    response = client.post(
        f"/api/v1/projects/{sample_project_id}/youtube/schedule",
        json={"publish_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat()},
    )

    assert response.status_code == 409


def test_cancel_scheduled_project_requires_existing_schedule(
    client: TestClient,
    sample_project_id: str,
) -> None:
    response = client.post(f"/api/v1/projects/{sample_project_id}/youtube/schedule/cancel")

    assert response.status_code == 400


def test_reject_project_publication_marks_review_as_rejected(
    client: TestClient,
    db_session: Session,
    sample_project_id: str,
) -> None:
    response = client.post(
        f"/api/v1/projects/{sample_project_id}/review/reject",
        json={"reviewer_name": "human-reviewer", "notes": "Precisa de ajustes"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["review_status"] == "rejected"

    project = db_session.scalar(
        select(VideoProjectModel).where(VideoProjectModel.id == sample_project_id)
    )
    assert project is not None
    assert project.review_status == ReviewStatus.REJECTED

    reviews = db_session.scalars(
        select(PublicationReviewModel).where(PublicationReviewModel.project_id == sample_project_id)
    ).all()
    assert len(reviews) == 1
    assert reviews[0].status == ReviewStatus.REJECTED
