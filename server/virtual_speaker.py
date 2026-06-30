"""Virtual speaker setup using VB-Audio Virtual Cable on Windows."""

from __future__ import annotations

import logging
import sys
import webbrowser
from dataclasses import dataclass

logger = logging.getLogger(__name__)

VBCABLE_DOWNLOAD = "https://vb-audio.com/Cable/"
VBCABLE_OUTPUT_MARKERS = ("cable input", "soundshare virtual")

_saved_default_device_id: str | None = None
_virtual_speaker_enabled = False
_active_output_name: str | None = None
_active_input_name: str | None = None


@dataclass(frozen=True)
class VirtualCableDevices:
    output_name: str
    output_id: str
    output_index: int
    loopback_name: str
    loopback_index: int


def is_virtual_speaker_enabled() -> bool:
    return _virtual_speaker_enabled


def get_virtual_speaker_info() -> dict:
    return {
        "enabled": _virtual_speaker_enabled,
        "output": _active_output_name,
        "input": _active_input_name,
    }


def _set_default_endpoint(device_id: str) -> None:
    import comtypes
    from comtypes import CLSCTX_ALL, GUID, HRESULT, COMMETHOD
    from ctypes import c_int, c_wchar_p

    class IPolicyConfig(comtypes.IUnknown):
        _iid_ = GUID("{f867966f-850a-48c9-8a7e-44ad20a1f408}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "SetDefaultEndpoint",
                (["in"], c_wchar_p, "deviceId"),
                (["in"], c_int, "role"),
            ),
        ]

    policy_config = comtypes.CoCreateInstance(
        GUID("{870af99c-1717-4897-be34-e51ad96571f4}"),
        IPolicyConfig,
        clsctx=CLSCTX_ALL,
    )
    for role in (0, 1, 2):
        policy_config.SetDefaultEndpoint(device_id, role)


def _list_pyaudio_devices(pa) -> tuple[list[dict], list[dict]]:
    import pyaudiowpatch as pyaudio

    outputs: list[dict] = []
    inputs: list[dict] = []
    wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    for index in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(index)
        if info.get("hostApi") != wasapi["index"]:
            continue
        if info.get("maxOutputChannels", 0) > 0 and not info.get(
            "isLoopbackDevice", False
        ):
            outputs.append(dict(info))
        if info.get("maxInputChannels", 0) > 0 and not info.get(
            "isLoopbackDevice", False
        ):
            inputs.append(dict(info))
    return outputs, inputs


def _name_matches(name: str, markers: tuple[str, ...]) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in markers)


def find_virtual_cable_devices(pa=None) -> VirtualCableDevices | None:
    if sys.platform != "win32":
        return None

    own_pa = pa is None
    if own_pa:
        import pyaudiowpatch as pyaudio

        pa = pyaudio.PyAudio()

    try:
        outputs, _inputs = _list_pyaudio_devices(pa)
        cable_output = next(
            (d for d in outputs if _name_matches(d["name"], VBCABLE_OUTPUT_MARKERS)),
            None,
        )
        cable_loopback = None
        for loopback in pa.get_loopback_device_info_generator():
            name = loopback["name"].lower()
            if "cable input" in name and "16ch" not in name:
                cable_loopback = dict(loopback)
                break

        if not cable_output or not cable_loopback:
            return None

        output_id = _lookup_device_id(cable_output["name"])
        return VirtualCableDevices(
            output_name=cable_output["name"],
            output_id=output_id or "",
            output_index=int(cable_output["index"]),
            loopback_name=cable_loopback["name"],
            loopback_index=int(cable_loopback["index"]),
        )
    finally:
        if own_pa:
            pa.terminate()


def _lookup_device_id(friendly_name: str) -> str | None:
    try:
        from pycaw.pycaw import AudioUtilities

        for device in AudioUtilities.GetAllDevices():
            if device.FriendlyName == friendly_name:
                return device.id
    except Exception as exc:
        logger.warning("Could not resolve device id for %s: %s", friendly_name, exc)
    return None


def get_current_default_output_id() -> str | None:
    try:
        from pycaw.pycaw import AudioUtilities

        speakers = AudioUtilities.GetSpeakers()
        return speakers.id if speakers else None
    except Exception:
        return None


def setup_virtual_speaker() -> dict:
    """Switch Windows default output to the virtual cable playback device."""
    global _saved_default_device_id, _virtual_speaker_enabled
    global _active_output_name, _active_input_name

    if sys.platform != "win32":
        return {"ok": False, "message": "Virtual speaker is Windows-only"}

    devices = find_virtual_cable_devices()
    if devices is None:
        return {
            "ok": False,
            "message": (
                "Virtual speaker driver not installed. "
                "Run install_virtual_speaker.bat once on this PC."
            ),
            "install_url": VBCABLE_DOWNLOAD,
        }

    if not devices.output_id:
        return {
            "ok": False,
            "message": f"Found {devices.output_name} but could not set it as default.",
        }

    if _saved_default_device_id is None:
        _saved_default_device_id = get_current_default_output_id()

    try:
        _set_default_endpoint(devices.output_id)
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Could not set virtual speaker as default output: {exc}",
        }

    _virtual_speaker_enabled = True
    _active_output_name = devices.output_name
    _active_input_name = devices.loopback_name
    logger.info(
        "Virtual speaker active: output=%s capture=%s",
        devices.output_name,
        devices.loopback_name,
    )
    return {
        "ok": True,
        "message": f"Virtual speaker: {devices.output_name}",
        "output": devices.output_name,
        "input": devices.loopback_name,
        "loopback_index": devices.loopback_index,
    }


def teardown_virtual_speaker() -> None:
    """Restore the previous default Windows output device."""
    global _saved_default_device_id, _virtual_speaker_enabled
    global _active_output_name, _active_input_name

    if _saved_default_device_id:
        try:
            _set_default_endpoint(_saved_default_device_id)
            logger.info("Restored previous default audio output")
        except Exception as exc:
            logger.warning("Could not restore default audio output: %s", exc)

    _saved_default_device_id = None
    _virtual_speaker_enabled = False
    _active_output_name = None
    _active_input_name = None


def open_install_page() -> None:
    webbrowser.open(VBCABLE_DOWNLOAD)


def probe_virtual_speaker() -> dict:
    devices = find_virtual_cable_devices()
    if devices is None:
        return {
            "ok": False,
            "mode": "virtual",
            "message": (
                "Install the free VB-Audio Virtual Cable once on this PC, "
                "then restart SoundShare."
            ),
            "install_url": VBCABLE_DOWNLOAD,
        }
    return {
        "ok": True,
        "mode": "virtual",
        "message": f"Ready: {devices.output_name}",
        "output": devices.output_name,
        "input": devices.loopback_name,
        "loopback_index": devices.loopback_index,
    }


def find_virtual_cable_loopback(pa) -> dict:
    """Return the WASAPI loopback device for CABLE Input."""
    devices = find_virtual_cable_devices(pa)
    if devices is None:
        raise RuntimeError(
            "Virtual speaker not installed. Run install_virtual_speaker.bat"
        )
    return pa.get_device_info_by_index(devices.loopback_index)
