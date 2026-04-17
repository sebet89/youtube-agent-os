from fastapi import APIRouter

from app.api.routes.analytics import router as analytics_router
from app.api.routes.content_generation import router as content_generation_router
from app.api.routes.health import router as health_router
from app.api.routes.media_assets import router as media_assets_router
from app.api.routes.oauth import router as oauth_router
from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.project_actions import router as project_actions_router
from app.api.routes.project_artifacts import router as project_artifacts_router
from app.api.routes.project_metadata import router as project_metadata_router
from app.api.routes.projects import router as projects_router
from app.api.routes.publishing import router as publishing_router
from app.api.routes.rendering import router as rendering_router
from app.api.routes.review_dashboard import router as review_dashboard_router
from app.api.routes.studio import router as studio_router
from app.api.routes.system_settings import router as system_settings_router

api_router = APIRouter()
api_router.include_router(analytics_router, tags=["analytics"])
api_router.include_router(content_generation_router, tags=["content"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(media_assets_router, tags=["media-assets"])
api_router.include_router(oauth_router, tags=["oauth"])
api_router.include_router(pipeline_router, tags=["pipeline"])
api_router.include_router(project_actions_router, tags=["project-actions"])
api_router.include_router(project_artifacts_router, tags=["project-artifacts"])
api_router.include_router(publishing_router, tags=["publishing"])
api_router.include_router(project_metadata_router, tags=["project-metadata"])
api_router.include_router(projects_router, tags=["projects"])
api_router.include_router(review_dashboard_router)
api_router.include_router(rendering_router, tags=["rendering"])
api_router.include_router(studio_router)
api_router.include_router(system_settings_router)
