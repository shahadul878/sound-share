"""Cloud / Railway deployment helpers."""

from __future__ import annotations

import os

from aiohttp import web


def is_railway() -> bool:
    return bool(
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        or os.environ.get("RAILWAY_SERVICE_NAME")
    )


def is_cloud_deploy() -> bool:
    if is_railway():
        return True
    return os.environ.get("SOUNDSHARE_CLOUD", "").lower() in ("1", "true", "yes")


def use_silent_audio() -> bool:
    explicit = os.environ.get("SOUNDSHARE_SILENT", "").lower()
    if explicit in ("1", "true", "yes"):
        return True
    if explicit in ("0", "false", "no"):
        return False
    return is_cloud_deploy()


def get_port(default: int = 8765) -> int:
    raw = os.environ.get("PORT")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_public_listener_url(request: web.Request | None = None) -> str:
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if domain:
        return f"https://{domain}/"

    if request is not None:
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip()
        host = request.headers.get("Host") or request.host
        if host:
            scheme = forwarded_proto or ("https" if not host.startswith("localhost") else "http")
            return f"{scheme}://{host}/"

    public = os.environ.get("SOUNDSHARE_PUBLIC_URL", "").strip()
    if public:
        return public if public.endswith("/") else f"{public}/"

    return ""


def get_host_dashboard_url(request: web.Request | None = None) -> str:
    listener = get_public_listener_url(request)
    if listener:
        return listener.rstrip("/") + "/host"
    port = get_port()
    return f"http://127.0.0.1:{port}/host"
