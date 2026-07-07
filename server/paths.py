"""Resolve application paths for development and frozen (PyInstaller) builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def get_web_dir() -> Path:
    return get_app_root() / "web"


def get_install_root() -> Path:
    """Directory where the executable lives."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_config_dir() -> Path:
    """Writable config directory (AppData when installed under Program Files)."""
    cloud_dir = os.environ.get("SOUNDSHARE_DATA_DIR", "").strip()
    if cloud_dir:
        config_dir = Path(cloud_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        config_dir = base / "SoundShare"
    else:
        config_dir = get_install_root()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
