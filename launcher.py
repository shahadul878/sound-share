"""
SoundShare desktop launcher.
Used as the PyInstaller entry point for the Windows executable.
"""

from __future__ import annotations

import sys
import threading
import time
import webbrowser


def _open_browser_later(port: int) -> None:
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{port}/panel")


def main() -> None:
    if len(sys.argv) == 1:
        sys.argv.extend(["--port", "8765"])

    port = 8765
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass

    threading.Thread(
        target=_open_browser_later, args=(port,), daemon=True, name="open-browser"
    ).start()

    from server.app import main as run_server

    run_server()


if __name__ == "__main__":
    main()
