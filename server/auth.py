"""Listener session tokens after password verification."""

from __future__ import annotations

import secrets
import time

from server.config import get_listener_password, password_required

_listener_sessions: dict[str, float] = {}
SESSION_TTL_SEC = 24 * 3600


def create_listener_session() -> str:
    token = secrets.token_urlsafe(32)
    _listener_sessions[token] = time.time() + SESSION_TTL_SEC
    return token


def validate_listener_session(token: str | None) -> bool:
    if not password_required():
        return True
    if not token:
        return False
    expiry = _listener_sessions.get(token)
    if not expiry:
        return False
    if time.time() > expiry:
        _listener_sessions.pop(token, None)
        return False
    return True


def verify_listener_password(password: str) -> bool:
    expected = get_listener_password()
    if not expected:
        return True
    if len(password) != len(expected):
        return False
    return secrets.compare_digest(password, expected)


def purge_expired_sessions() -> None:
    now = time.time()
    expired = [t for t, exp in _listener_sessions.items() if now > exp]
    for t in expired:
        _listener_sessions.pop(t, None)
