"""SoundShare WebRTC signaling server."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import socket
from pathlib import Path

import qrcode
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration
from aiortc.rtcconfiguration import RTCIceServer

from server.audio import (
    configure_capture,
    get_capture_status,
    get_relayed_track,
    probe_audio_devices,
    shutdown_audio,
)
from server.virtual_speaker import setup_virtual_speaker, teardown_virtual_speaker

from server.paths import get_web_dir

logger = logging.getLogger(__name__)

WEB_DIR = get_web_dir()
DEFAULT_PORT = 8765

pcs: set[RTCPeerConnection] = set()


def get_lan_ip() -> str:
    """Best-effort LAN IP for sharing the listener URL."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def load_ice_servers() -> list[RTCIceServer]:
    raw = os.environ.get("SOUNDSHARE_ICE_SERVERS")
    if raw:
        try:
            entries = json.loads(raw)
            return [RTCIceServer(**entry) for entry in entries]
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Invalid SOUNDSHARE_ICE_SERVERS: %s", exc)
    return [RTCIceServer(urls="stun:stun.l.google.com:19302")]


def print_startup_banner(host: str, port: int, capture_mode: str) -> None:
    lan_ip = get_lan_ip()
    local_url = f"http://127.0.0.1:{port}"
    lan_url = f"http://{lan_ip}:{port}"

    print()
    print("=" * 52)
    print("  SoundShare v1.0 — by H M Shahadul Islam")
    print("=" * 52)
    print(f"  Local:   {local_url}")
    print(f"  Network: {lan_url}")
    print()
    print("  Share the Network URL with listeners on your Wi-Fi.")
    print("  They open it in a browser and tap Connect & Play.")
    print("=" * 52)
    print()

    qr = qrcode.QRCode(border=1)
    qr.add_data(lan_url)
    qr.make(fit=True)
    try:
        qr.print_ascii(invert=True)
    except UnicodeEncodeError:
        print(f"  QR code URL: {lan_url}")
    print()

    audio = probe_audio_devices(capture_mode)
    if capture_mode == "virtual":
        print("  Mode: Virtual speaker (no physical speakers required)")
    else:
        print("  Mode: Loopback (captures default PC speakers)")

    if audio.get("ok"):
        print(f"  Audio capture: {audio['message']}")
        if capture_mode == "virtual" and audio.get("output"):
            print(f"  Windows output switched to: {audio['output']}")
            print("  All PC apps now play into SoundShare virtual speaker.")
    else:
        print("  !!! VIRTUAL SPEAKER NOT READY !!!")
        print(f"  {audio['message']}")
        print()
        if capture_mode == "virtual":
            print("  One-time setup on this PC:")
            print("  1. Double-click install_virtual_speaker.bat")
            print("  2. Install VB-Audio Virtual Cable (free)")
            print("  3. Restart SoundShare")
        else:
            print("  Fix on this PC:")
            print("  1. Plug in speakers/headphones OR enable your monitor audio")
            print("  2. Settings > System > Sound > choose an Output device")
            print("  3. Play a test sound, then restart SoundShare")
            print("  Quick open: start ms-settings:sound")
    print()


async def index(_request: web.Request) -> web.Response:
    return web.FileResponse(WEB_DIR / "index.html")


async def static_files(request: web.Request) -> web.Response:
    name = request.match_info.get("name", "")
    path = (WEB_DIR / name).resolve()
    if not str(path).startswith(str(WEB_DIR.resolve())):
        raise web.HTTPForbidden()
    if not path.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(path)


async def status(_request: web.Request) -> web.Response:
    connected = sum(1 for pc in pcs if pc.connectionState == "connected")
    capture = get_capture_status()
    return web.json_response(
        {
            "listeners": connected,
            "peers": len(pcs),
            "capture": capture["state"],
            "capture_error": capture["error"],
            "audio_level": capture["level"],
            "capture_mode": capture["mode"],
        }
    )


async def wait_for_ice_gathering(pc: RTCPeerConnection, timeout: float = 5.0) -> None:
    if pc.iceGatheringState == "complete":
        return
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while pc.iceGatheringState != "complete":
        if loop.time() >= deadline:
            logger.warning("ICE gathering timed out, continuing anyway")
            return
        await asyncio.sleep(0.05)


async def offer(request: web.Request) -> web.Response:
    params = await request.json()
    offer_sdp = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection(
        configuration=RTCConfiguration(iceServers=load_ice_servers())
    )
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange() -> None:
        logger.info("Peer connection state: %s", pc.connectionState)
        if pc.connectionState in ("failed", "closed", "disconnected"):
            await close_peer(pc)

    await pc.setRemoteDescription(offer_sdp)

    track = get_relayed_track()
    pc.addTrack(track)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    await wait_for_ice_gathering(pc)

    return web.json_response(
        {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
        }
    )


async def close_peer(pc: RTCPeerConnection) -> None:
    if pc in pcs:
        pcs.discard(pc)
    await pc.close()


async def on_shutdown(_app: web.Application) -> None:
    await asyncio.gather(*[close_peer(pc) for pc in list(pcs)], return_exceptions=True)
    shutdown_audio()
    teardown_virtual_speaker()


async def about(_request: web.Request) -> web.Response:
    return web.FileResponse(WEB_DIR / "about.html")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/about", about)
    app.router.add_get("/status", status)
    app.router.add_post("/offer", offer)
    app.router.add_get("/web/{name}", static_files)
    app.on_shutdown.append(on_shutdown)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="SoundShare WebRTC audio server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP port")
    parser.add_argument(
        "--loopback",
        action="store_true",
        help="Capture from physical speakers instead of virtual speaker",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    capture_mode = "loopback" if args.loopback else "virtual"

    if capture_mode == "virtual":
        setup = setup_virtual_speaker()
        configure_capture("virtual")
    else:
        configure_capture("loopback")

    print_startup_banner(args.host, args.port, capture_mode)
    app = create_app()
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
