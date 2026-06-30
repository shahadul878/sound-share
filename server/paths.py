"""Resolve application paths for development and frozen (PyInstaller) builds."""

from __future__ import annotations

import sys
from pathlib import Path


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def get_web_dir() -> Path:
    return get_app_root() / "web"


def get_install_root() -> Path:
    """Directory where the executable lives (for logs, config)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
