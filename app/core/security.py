from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import cast

from cryptography.fernet import Fernet


class InvalidStateError(ValueError):
    """Raised when an OAuth state token is invalid or tampered with."""


class TokenCipher:
    def __init__(self, secret_key: str) -> None:
        derived_key = hashlib.sha256(secret_key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(derived_key))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")


class SignedStateManager:
    def __init__(self, secret_key: str, ttl_seconds: int) -> None:
        self._secret_key = secret_key.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def generate(self, extra_payload: Mapping[str, int | str] | None = None) -> str:
        expires_at = datetime.now(UTC) + timedelta(seconds=self._ttl_seconds)
        payload = {
            "exp": int(expires_at.timestamp()),
            "nonce": secrets.token_urlsafe(16),
        }
        if extra_payload is not None:
            payload.update(dict(extra_payload))
        raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_part = base64.urlsafe_b64encode(raw_payload).decode("utf-8").rstrip("=")
        signature = hmac.new(
            self._secret_key,
            payload_part.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature_part = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        return f"{payload_part}.{signature_part}"

    def verify(self, state: str) -> dict[str, int | str]:
        try:
            payload_part, signature_part = state.split(".", maxsplit=1)
        except ValueError as exc:
            raise InvalidStateError("OAuth state is malformed.") from exc

        expected_signature = hmac.new(
            self._secret_key,
            payload_part.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        actual_signature = self._decode_base64(signature_part)

        if not hmac.compare_digest(expected_signature, actual_signature):
            raise InvalidStateError("OAuth state signature is invalid.")

        payload = cast(
            Mapping[str, int | str],
            json.loads(self._decode_base64(payload_part).decode("utf-8")),
        )
        expires_at = datetime.fromtimestamp(int(payload["exp"]), UTC)
        if expires_at < datetime.now(UTC):
            raise InvalidStateError("OAuth state has expired.")

        return dict(payload)

    @staticmethod
    def _decode_base64(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(f"{value}{padding}")
