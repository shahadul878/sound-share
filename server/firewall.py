"""Windows Firewall helpers for WebRTC (UDP) and HTTP signaling (TCP)."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

RULE_TCP = "SoundShare HTTP"
RULE_APP_IN = "SoundShare App In"
RULE_APP_OUT = "SoundShare App Out"


def _run_netsh(args: list[str]) -> bool:
    try:
        result = subprocess.run(
            ["netsh", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except OSError as exc:
        logger.debug("netsh unavailable: %s", exc)
        return False


def _delete_rule(name: str) -> None:
    _run_netsh(["advfirewall", "firewall", "delete", "rule", f"name={name}"])


def ensure_firewall_rules(exe_path: Path | None = None, port: int = 8765) -> None:
    """Allow SoundShare HTTP + WebRTC media through Windows Firewall."""
    if sys.platform != "win32":
        return

    _delete_rule("SoundShare")  # legacy rule name
    _delete_rule(RULE_TCP)
    _delete_rule(RULE_APP_IN)
    _delete_rule(RULE_APP_OUT)

    _run_netsh(
        [
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={RULE_TCP}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={port}",
            "profile=any",
            "enable=yes",
        ]
    )

    if exe_path and exe_path.is_file():
        exe = str(exe_path.resolve())
        for rule_name, direction in ((RULE_APP_IN, "in"), (RULE_APP_OUT, "out")):
            _run_netsh(
                [
                    "advfirewall",
                    "firewall",
                    "add",
                    "rule",
                    f"name={rule_name}",
                    f"dir={direction}",
                    "action=allow",
                    f"program={exe}",
                    "profile=any",
                    "enable=yes",
                ]
            )
        logger.info("Firewall rules updated for %s", exe)
