from app.domain.entities import PublicationReview, VideoProject
from app.domain.enums import ReviewStatus, VideoVisibility
from app.domain.exceptions import HumanReviewRequiredError


def test_video_project_requires_human_approval_before_publication() -> None:
    project = VideoProject(idea_id="idea-1")

    try:
        project.publish_publicly()
    except HumanReviewRequiredError:
        pass
    else:
        raise AssertionError("Expected human review to be required before public publication.")


def test_video_project_can_publish_after_human_approval() -> None:
    review = PublicationReview()
    review.approve(reviewer_name="editor@example.com", notes="Looks good")

    project = VideoProject(idea_id="idea-1", review_status=review.status)
    project.publish_publicly()

    assert review.status == ReviewStatus.APPROVED
    assert project.visibility == VideoVisibility.PUBLIC
    assert project.published_at is not None
