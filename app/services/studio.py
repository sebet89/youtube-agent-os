from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import YoutubeChannelConnectionModel
from app.domain.enums import ChannelConnectionStatus


@dataclass(slots=True)
class StudioConnectionSummary:
    connection_id: str
    youtube_channel_id: str
    channel_title: str
    connection_status: str


@dataclass(slots=True)
class StudioDashboardSnapshot:
    connections: list[StudioConnectionSummary]


class StudioDashboardService:
    def get_snapshot(self, session: Session) -> StudioDashboardSnapshot:
        connection_query = (
            select(YoutubeChannelConnectionModel)
            .where(
                YoutubeChannelConnectionModel.connection_status
                == ChannelConnectionStatus.ACTIVE
            )
            .order_by(YoutubeChannelConnectionModel.created_at.desc())
        )
        connections = list(session.scalars(connection_query))

        return StudioDashboardSnapshot(
            connections=[
                StudioConnectionSummary(
                    connection_id=connection.id,
                    youtube_channel_id=connection.youtube_channel_id,
                    channel_title=connection.channel_title,
                    connection_status=connection.connection_status.value,
                )
                for connection in connections
            ],
        )
