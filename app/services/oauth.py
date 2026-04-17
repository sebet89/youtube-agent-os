from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import InvalidStateError, SignedStateManager, TokenCipher
from app.db.models import YoutubeChannelConnectionModel
from app.db.repositories import YoutubeChannelConnectionRepository
from app.domain.enums import ChannelConnectionStatus
from app.services.interfaces import YoutubeAuthProvider


@dataclass(slots=True)
class YoutubeOAuthStart:
    authorization_url: str
    state: str


@dataclass(slots=True)
class YoutubeOAuthCallbackResult:
    connection_id: str
    youtube_channel_id: str
    channel_title: str
    connection_status: str
    scopes: list[str]
    token_expires_at: datetime | None


class YoutubeOAuthService:
    def __init__(
        self,
        provider: YoutubeAuthProvider,
        state_manager: SignedStateManager,
        token_cipher: TokenCipher,
    ) -> None:
        self._provider = provider
        self._state_manager = state_manager
        self._token_cipher = token_cipher

    def build_authorization_start(self) -> YoutubeOAuthStart:
        code_verifier = secrets.token_urlsafe(48)
        state = self._state_manager.generate(extra_payload={"cv": code_verifier})
        authorization_url = self._provider.build_authorization_url(
            state=state,
            code_verifier=code_verifier,
        )
        return YoutubeOAuthStart(authorization_url=authorization_url, state=state)

    def handle_callback(
        self,
        session: Session,
        *,
        state: str,
        code: str,
    ) -> YoutubeOAuthCallbackResult:
        state_payload = self._state_manager.verify(state)
        code_verifier = str(state_payload["cv"])
        connection_payload = self._provider.exchange_code_for_connection(
            code=code,
            code_verifier=code_verifier,
        )
        repository = YoutubeChannelConnectionRepository(session)
        connection = repository.upsert_connection(
            youtube_channel_id=connection_payload.youtube_channel_id,
            channel_title=connection_payload.channel_title,
            oauth_subject=connection_payload.oauth_subject,
            access_token_encrypted=self._token_cipher.encrypt(connection_payload.access_token),
            refresh_token_encrypted=(
                self._token_cipher.encrypt(connection_payload.refresh_token)
                if connection_payload.refresh_token
                else None
            ),
            token_expires_at=connection_payload.token_expires_at,
            scopes=connection_payload.scopes,
            connection_status=ChannelConnectionStatus.ACTIVE,
        )
        session.commit()
        session.refresh(connection)
        return self._build_result(connection)

    @staticmethod
    def _build_result(connection: YoutubeChannelConnectionModel) -> YoutubeOAuthCallbackResult:
        return YoutubeOAuthCallbackResult(
            connection_id=connection.id,
            youtube_channel_id=connection.youtube_channel_id,
            channel_title=connection.channel_title,
            connection_status=connection.connection_status.value,
            scopes=connection.scopes,
            token_expires_at=connection.token_expires_at,
        )


__all__ = [
    "InvalidStateError",
    "YoutubeOAuthCallbackResult",
    "YoutubeOAuthService",
    "YoutubeOAuthStart",
]
