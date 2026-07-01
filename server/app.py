"""SoundShare WebRTC signaling server."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import secrets
import socket
import time

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
from server.auth import (
    create_listener_session,
    purge_expired_sessions,
    validate_listener_session,
    verify_listener_password,
)
from server.config import (
    block_client,
    get_listener_password,
    get_owner_token,
    is_blocked,
    load_config,
    password_required,
    save_config,
    unblock_client,
)
from server.paths import get_web_dir
from server.peers import peer_registry
from server.virtual_speaker import setup_virtual_speaker, teardown_virtual_speaker

logger = logging.getLogger(__name__)

WEB_DIR = get_web_dir()
DEFAULT_PORT = 8765


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


def _client_ip(request: web.Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    peername = request.transport.get_extra_info("peername") if request.transport else None
    if peername:
        return peername[0]
    return "unknown"


def _is_localhost(request: web.Request) -> bool:
    ip = _client_ip(request)
    return ip in ("127.0.0.1", "::1", "localhost")


def _tokens_match(provided: str, expected: str) -> bool:
    if not provided or not expected:
        return False
    if len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


def _require_owner(request: web.Request) -> web.Response | None:
    if _is_localhost(request):
        return None
    token = request.headers.get("X-Owner-Token") or request.query.get("token", "")
    if not _tokens_match(token, get_owner_token()):
        return web.json_response({"error": "Unauthorized"}, status=401)
    return None


def print_startup_banner(host: str, port: int, capture_mode: str) -> None:
    lan_ip = get_lan_ip()
    local_url = f"http://127.0.0.1:{port}"
    lan_url = f"http://{lan_ip}:{port}"
    panel_url = f"{local_url}/host"

    print()
    print("=" * 52)
    print("  SoundShare v1.1 — by H M Shahadul Islam")
    print("=" * 52)
    print(f"  Local:   {local_url}")
    print(f"  Network: {lan_url}")
    print(f"  Host:    {panel_url}")
    print(f"  Panel:   {local_url}/panel")
    print()
    if password_required():
        print("  Listener password: ENABLED")
    else:
        print("  Listener password: OFF (open access)")
    print()
    print("  Host dashboard opens automatically on this PC.")
    print(f"  Owner panel (devices & password): {local_url}/panel")
    print(f"  Owner token (remote panel access): {get_owner_token()}")
    print()
    print("  Share the Network URL with listeners on your Wi-Fi.")
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
    else:
        print("  !!! VIRTUAL SPEAKER NOT READY !!!")
        print(f"  {audio['message']}")
    print()


async def index(_request: web.Request) -> web.Response:
    return web.FileResponse(WEB_DIR / "index.html")


async def host_page(_request: web.Request) -> web.Response:
    return web.FileResponse(WEB_DIR / "host.html")


async def host_info(request: web.Request) -> web.Response:
    host = request.host or f"127.0.0.1:{DEFAULT_PORT}"
    hostname = host.split(":")[0]
    port = host.split(":")[1] if ":" in host else str(DEFAULT_PORT)
    lan_ip = get_lan_ip()
    capture = get_capture_status()
    return web.json_response(
        {
            "local_url": f"http://127.0.0.1:{port}/",
            "network_url": f"http://{lan_ip}:{port}/",
            "listeners": peer_registry.connected_count(),
            "password_required": password_required(),
            "capture": capture["state"],
            "capture_error": capture["error"],
            "audio_level": capture["level"],
            "is_localhost": _is_localhost(request),
        }
    )


async def panel_page(_request: web.Request) -> web.Response:
    return web.FileResponse(WEB_DIR / "panel.html")


async def static_files(request: web.Request) -> web.Response:
    name = request.match_info.get("name", "")
    path = (WEB_DIR / name).resolve()
    if not str(path).startswith(str(WEB_DIR.resolve())):
        raise web.HTTPForbidden()
    if not path.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(path)


async def status(_request: web.Request) -> web.Response:
    connected = peer_registry.connected_count()
    capture = get_capture_status()
    return web.json_response(
        {
            "listeners": connected,
            "peers": len(peer_registry.list_peers()),
            "capture": capture["state"],
            "capture_error": capture["error"],
            "audio_level": capture["level"],
            "capture_mode": capture["mode"],
            "password_required": password_required(),
        }
    )


async def auth_status(_request: web.Request) -> web.Response:
    purge_expired_sessions()
    return web.json_response(
        {
            "password_required": password_required(),
        }
    )


async def auth_verify(request: web.Request) -> web.Response:
    purge_expired_sessions()
    if not password_required():
        return web.json_response({"ok": True, "token": create_listener_session()})

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    password = str(body.get("password", ""))
    if not verify_listener_password(password):
        return web.json_response({"error": "Wrong password"}, status=401)

    return web.json_response({"ok": True, "token": create_listener_session()})


async def panel_settings_get(request: web.Request) -> web.Response:
    denied = _require_owner(request)
    if denied:
        return denied
    cfg = load_config()
    return web.json_response(
        {
            "password_required": password_required(),
            "blocked_count": len(cfg.get("blocked_client_ids", [])),
            "owner_token": get_owner_token(),
        }
    )


async def panel_settings_put(request: web.Request) -> web.Response:
    denied = _require_owner(request)
    if denied:
        return denied

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    cfg = load_config()

    if "password_enabled" in body:
        enabled = bool(body["password_enabled"])
        if not enabled:
            cfg["listener_password"] = None
        elif body.get("password"):
            cfg["listener_password"] = str(body["password"]).strip()
        elif not cfg.get("listener_password"):
            return web.json_response(
                {"error": "Set a password when enabling protection"}, status=400
            )

    if body.get("password") and body.get("password_enabled", True):
        pwd = str(body["password"]).strip()
        if pwd:
            cfg["listener_password"] = pwd

    if body.get("regenerate_owner_token"):
        cfg["owner_token"] = secrets.token_urlsafe(24)

    save_config(cfg)
    return web.json_response(
        {
            "ok": True,
            "password_required": password_required(),
            "owner_token": get_owner_token(),
        }
    )


async def panel_devices(request: web.Request) -> web.Response:
    denied = _require_owner(request)
    if denied:
        return denied
    cfg = load_config()
    return web.json_response(
        {
            "devices": peer_registry.list_peers(),
            "blocked_client_ids": cfg.get("blocked_client_ids", []),
            "listeners": peer_registry.connected_count(),
            "password_required": password_required(),
            "server_time": time.time(),
        }
    )


async def panel_kick(request: web.Request) -> web.Response:
    denied = _require_owner(request)
    if denied:
        return denied

    peer_id = request.match_info["peer_id"]
    record = peer_registry.get(peer_id)
    if not record:
        return web.json_response({"error": "Device not found"}, status=404)

    await close_peer(record.pc)
    return web.json_response({"ok": True, "action": "kicked", "peer_id": peer_id})


async def panel_block(request: web.Request) -> web.Response:
    denied = _require_owner(request)
    if denied:
        return denied

    peer_id = request.match_info["peer_id"]
    record = peer_registry.get(peer_id)
    if not record:
        return web.json_response({"error": "Device not found"}, status=404)

    block_client(record.client_id, record.ip)
    await close_peer(record.pc)
    return web.json_response(
        {
            "ok": True,
            "action": "blocked",
            "peer_id": peer_id,
            "client_id": record.client_id,
        }
    )


async def panel_unblock(request: web.Request) -> web.Response:
    denied = _require_owner(request)
    if denied:
        return denied

    client_id = request.match_info["client_id"]
    unblock_client(client_id)
    return web.json_response({"ok": True, "client_id": client_id})


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
    purge_expired_sessions()

    try:
        params = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    listener_token = params.get("listener_token") or request.headers.get(
        "X-Listener-Token"
    )
    if not validate_listener_session(listener_token):
        return web.json_response({"error": "Password required or session expired"}, status=401)

    client_id = str(params.get("client_id", "unknown")).strip() or "unknown"
    device_name = str(params.get("device_name", "Listener")).strip() or "Listener"
    ip = _client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    if is_blocked(client_id, ip):
        return web.json_response({"error": "Device blocked by owner"}, status=403)

    offer_sdp = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection(
        configuration=RTCConfiguration(iceServers=load_ice_servers())
    )
    record = peer_registry.register(
        pc,
        client_id=client_id,
        device_name=device_name,
        ip=ip,
        user_agent=user_agent,
    )
    logger.info(
        "New listener %s (%s) from %s [%s]",
        record.device_name,
        record.client_id[:8],
        record.ip,
        record.peer_id,
    )

    @pc.on("connectionstatechange")
    async def on_connectionstatechange() -> None:
        peer_registry.update_state(pc, pc.connectionState)
        logger.info(
            "Peer %s (%s): %s",
            record.device_name,
            record.peer_id,
            pc.connectionState,
        )
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
            "peer_id": record.peer_id,
        }
    )


async def close_peer(pc: RTCPeerConnection) -> None:
    record = peer_registry.remove_pc(pc)
    if record:
        logger.info("Closed peer %s (%s)", record.device_name, record.peer_id)
    await pc.close()


async def on_shutdown(_app: web.Application) -> None:
    await asyncio.gather(
        *[close_peer(pc) for pc in peer_registry.all_pcs()],
        return_exceptions=True,
    )
    shutdown_audio()
    teardown_virtual_speaker()


async def about(_request: web.Request) -> web.Response:
    return web.FileResponse(WEB_DIR / "about.html")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/host", host_page)
    app.router.add_get("/panel", panel_page)
    app.router.add_get("/about", about)
    app.router.add_get("/status", status)
    app.router.add_get("/api/host/info", host_info)
    app.router.add_get("/api/auth/status", auth_status)
    app.router.add_post("/api/auth/verify", auth_verify)
    app.router.add_get("/api/panel/settings", panel_settings_get)
    app.router.add_put("/api/panel/settings", panel_settings_put)
    app.router.add_get("/api/panel/devices", panel_devices)
    app.router.add_post("/api/panel/devices/{peer_id}/kick", panel_kick)
    app.router.add_post("/api/panel/devices/{peer_id}/block", panel_block)
    app.router.add_post("/api/panel/blocked/{client_id}/unblock", panel_unblock)
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
    parser.add_argument(
        "--password",
        default=None,
        help="Require this password for listeners (saved to config)",
    )
    parser.add_argument(
        "--no-password",
        action="store_true",
        help="Disable listener password protection",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.no_password:
        cfg = load_config()
        cfg["listener_password"] = None
        save_config(cfg)
    elif args.password:
        cfg = load_config()
        cfg["listener_password"] = args.password.strip()
        save_config(cfg)

    capture_mode = "loopback" if args.loopback else "virtual"

    if capture_mode == "virtual":
        setup_virtual_speaker()
        configure_capture("virtual")
    else:
        configure_capture("loopback")

    print_startup_banner(args.host, args.port, capture_mode)
    app = create_app()
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
