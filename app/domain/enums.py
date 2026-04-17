from enum import StrEnum


class VideoVisibility(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"
    UNLISTED = "unlisted"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ChannelConnectionStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"


class VideoIdeaStatus(StrEnum):
    DRAFT = "draft"
    BRIEFING_READY = "briefing_ready"
    SCRIPT_READY = "script_ready"
    METADATA_READY = "metadata_ready"
    PRODUCTION_READY = "production_ready"
    RENDER_READY = "render_ready"
    RENDERED = "rendered"
    UPLOADED = "uploaded"
    PUBLISHED = "published"


class MediaAssetStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
