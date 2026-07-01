"""Prevent multiple SoundShare instances on Windows."""

from __future__ import annotations

import sys

_acquired_in_process = False


def ensure_single_instance() -> bool:
    """Return False if another instance is already running."""
    global _acquired_in_process

    if _acquired_in_process:
        return True

    if sys.platform != "win32":
        _acquired_in_process = True
        return True

    import ctypes

    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, "Global\\SoundShare.SingleInstance")
    last_error = kernel32.GetLastError()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        print()
        print("  SoundShare is already running.")
        print("  Close the other window first, or end SoundShare.exe in Task Manager.")
        print()
        return False

    _acquired_in_process = True
    return True
