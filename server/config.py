"""Persistent SoundShare settings (password, owner token, block list)."""

from __future__ import annotations

import json
import logging
import os
import secrets
import shutil
from pathlib import Path
from typing import Any

from server.paths import get_config_dir, get_install_root

logger = logging.getLogger(__name__)

CONFIG_FILE = "soundshare_config.json"


def _config_path() -> Path:
    return get_config_dir() / CONFIG_FILE


def _legacy_config_path() -> Path:
    return get_install_root() / CONFIG_FILE


def _migrate_legacy_config() -> None:
    """Move config from Program Files to AppData (one-time, installed builds)."""
    legacy = _legacy_config_path()
    target = _config_path()
    if legacy.is_file() and not target.is_file():
        try:
            shutil.copy2(legacy, target)
            logger.info("Migrated config to %s", target)
        except OSError as exc:
            logger.warning("Could not migrate legacy config: %s", exc)


def _default_config() -> dict[str, Any]:
    return {
        "listener_password": None,
        "owner_token": secrets.token_urlsafe(24),
        "blocked_client_ids": [],
        "blocked_ips": [],
    }


def load_config() -> dict[str, Any]:
    _migrate_legacy_config()
    path = _config_path()
    if not path.is_file():
        cfg = _default_config()
        save_config(cfg)
        return cfg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {}
    base = _default_config()
    base.update({k: v for k, v in data.items() if k in base})

    owner_env = os.environ.get("SOUNDSHARE_OWNER_TOKEN", "").strip()
    if owner_env:
        base["owner_token"] = owner_env

    if "SOUNDSHARE_LISTENER_PASSWORD" in os.environ:
        pwd_env = os.environ.get("SOUNDSHARE_LISTENER_PASSWORD", "").strip()
        base["listener_password"] = pwd_env or None

    if not base.get("owner_token"):
        base["owner_token"] = secrets.token_urlsafe(24)
        save_config(base)
    return base


def save_config(cfg: dict[str, Any]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def password_required() -> bool:
    pwd = load_config().get("listener_password")
    return bool(pwd and str(pwd).strip())


def get_listener_password() -> str | None:
    pwd = load_config().get("listener_password")
    if pwd and str(pwd).strip():
        return str(pwd)
    return None


def get_owner_token() -> str:
    return str(load_config().get("owner_token", ""))


def is_blocked(client_id: str | None, ip: str | None) -> bool:
    cfg = load_config()
    if client_id and client_id in cfg.get("blocked_client_ids", []):
        return True
    if ip and ip in cfg.get("blocked_ips", []):
        return True
    return False


def block_client(client_id: str, ip: str | None) -> None:
    cfg = load_config()
    ids = list(cfg.get("blocked_client_ids", []))
    if client_id and client_id not in ids:
        ids.append(client_id)
    cfg["blocked_client_ids"] = ids
    if ip:
        ips = list(cfg.get("blocked_ips", []))
        if ip not in ips:
            ips.append(ip)
        cfg["blocked_ips"] = ips
    save_config(cfg)


def unblock_client(client_id: str) -> None:
    cfg = load_config()
    ids = [x for x in cfg.get("blocked_client_ids", []) if x != client_id]
    cfg["blocked_client_ids"] = ids
    save_config(cfg)
