"""Shared Tactile service account (Singapore production)."""
from __future__ import annotations

import time

from app.config import settings
from app.tactile_client import TactileClient

_token_cache: str | None = None
_token_at: float = 0


async def get_service_client() -> TactileClient:
    global _token_cache, _token_at
    if not settings.tactile_service_email or not settings.tactile_service_password:
        raise RuntimeError("TACTILE_SERVICE_EMAIL/PASSWORD not configured")
    if _token_cache and (time.time() - _token_at) < 3600:
        return TactileClient(_token_cache)
    client = TactileClient()
    auth = await client.login(settings.tactile_service_email, settings.tactile_service_password)
    _token_cache = auth["access_token"]
    _token_at = time.time()
    return TactileClient(_token_cache)


def get_workspace_id() -> int:
    if not settings.tactile_workspace_id:
        raise RuntimeError("TACTILE_WORKSPACE_ID not configured — run bootstrap")
    return settings.tactile_workspace_id


def get_agent_id() -> int:
    if not settings.tactile_agent_id:
        raise RuntimeError("TACTILE_AGENT_ID not configured — run bootstrap")
    return settings.tactile_agent_id
