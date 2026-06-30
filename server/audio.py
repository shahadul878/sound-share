"""WASAPI loopback capture and WebRTC audio track."""

from __future__ import annotations

import asyncio
import logging
import queue
import sys
import threading
import time
from fractions import Fraction

import av
import numpy as np
from aiortc import MediaStreamTrack
from aiortc.contrib.media import MediaRelay

logger = logging.getLogger(__name__)

SAMPLE_RATE = 48000
CHANNELS = 2
FRAME_SAMPLES = 960  # 20 ms at 48 kHz
TIME_BASE = Fraction(1, SAMPLE_RATE)

_capture_mode = "virtual"  # "virtual" | "loopback"


def configure_capture(mode: str) -> None:
    global _capture_mode
    _capture_mode = mode


def get_capture_mode() -> str:
    return _capture_mode


def _resample_stereo(samples: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    if from_rate == to_rate or len(samples) == 0:
        return samples
    new_len = int(len(samples) * to_rate / from_rate)
    if new_len <= 0:
        return samples
    x_old = np.linspace(0.0, 1.0, len(samples), endpoint=False)
    x_new = np.linspace(0.0, 1.0, new_len, endpoint=False)
    left = np.interp(x_new, x_old, samples[:, 0])
    right = np.interp(x_new, x_old, samples[:, 1])
    return np.column_stack([left, right])


class LoopbackAudioTrack(MediaStreamTrack):
    """Captures system audio via WASAPI loopback and exposes it as a WebRTC track."""

    kind = "audio"
    capture_state = "starting"
    capture_error: str | None = None
    audio_level: float = 0.0

    def __init__(self) -> None:
        super().__init__()
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=64)
        self._pts = 0
        self._start_time: float | None = None
        self._stop_event = threading.Event()
        self._last_error_log = 0.0
        self._capture_thread = threading.Thread(
            target=self._capture_loop, name="loopback-capture", daemon=True
        )
        self._capture_thread.start()

    def _log_capture_error(self, message: str) -> None:
        LoopbackAudioTrack.capture_state = "error"
        LoopbackAudioTrack.capture_error = message
        now = time.time()
        if now - self._last_error_log >= 30:
            logger.error("%s", message)
            self._last_error_log = now

    def _read_stream_loop(
        self, stream, device_rate: int, device_channels: int
    ) -> None:
        LoopbackAudioTrack.capture_state = "live"
        LoopbackAudioTrack.capture_error = None
        while not self._stop_event.is_set():
            raw = stream.read(FRAME_SAMPLES, exception_on_overflow=False)
            samples = np.frombuffer(raw, dtype=np.int16)
            if device_channels == 1:
                samples = samples.reshape(-1, 1)
                samples = np.column_stack([samples[:, 0], samples[:, 0]])
            else:
                samples = samples.reshape(-1, device_channels)[:, :2]

            frame = samples.astype(np.float32) / 32768.0
            if device_rate != SAMPLE_RATE:
                frame = _resample_stereo(frame, device_rate, SAMPLE_RATE)

            try:
                self._queue.put(frame, timeout=0.5)
            except queue.Full:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._queue.put_nowait(frame)
                except queue.Full:
                    pass

    def _capture_with_virtual_cable(self) -> None:
        import pyaudiowpatch as pyaudio

        from server.virtual_speaker import find_virtual_cable_loopback

        pa = pyaudio.PyAudio()
        try:
            device = find_virtual_cable_loopback(pa)
            device_rate = int(device["defaultSampleRate"])
            device_channels = min(int(device["maxInputChannels"]), CHANNELS) or CHANNELS
            logger.info(
                "Capturing virtual speaker loopback: %s (%s Hz, %s ch)",
                device["name"],
                device_rate,
                device_channels,
            )

            stream = pa.open(
                format=pyaudio.paInt16,
                channels=device_channels,
                rate=device_rate,
                frames_per_buffer=FRAME_SAMPLES,
                input=True,
                input_device_index=int(device["index"]),
            )
            try:
                self._read_stream_loop(stream, device_rate, device_channels)
            finally:
                stream.stop_stream()
                stream.close()
        finally:
            pa.terminate()

    def _capture_with_pyaudiowpatch(self) -> None:
        import pyaudiowpatch as pyaudio

        pa = pyaudio.PyAudio()
        try:
            device = self._find_wasapi_loopback(pa)
            device_rate = int(device["defaultSampleRate"])
            device_channels = min(int(device["maxInputChannels"]), CHANNELS) or CHANNELS
            logger.info(
                "Capturing loopback via WASAPI: %s (%s Hz, %s ch)",
                device["name"],
                device_rate,
                device_channels,
            )

            stream = pa.open(
                format=pyaudio.paInt16,
                channels=device_channels,
                rate=device_rate,
                frames_per_buffer=FRAME_SAMPLES,
                input=True,
                input_device_index=device["index"],
            )
            try:
                self._read_stream_loop(stream, device_rate, device_channels)
            finally:
                stream.stop_stream()
                stream.close()
        finally:
            pa.terminate()

    def _find_wasapi_loopback(self, pa) -> dict:
        import pyaudiowpatch as pyaudio

        try:
            return pa.get_default_wasapi_loopback()
        except (OSError, LookupError):
            pass

        loopbacks = list(pa.get_loopback_device_info_generator())
        if not loopbacks:
            raise RuntimeError(
                "No WASAPI loopback devices found. "
                "Enable a playback device in Windows Sound settings."
            )

        try:
            wasapi = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out_idx = wasapi["defaultOutputDevice"]
            if default_out_idx >= 0:
                default_out = pa.get_device_info_by_index(default_out_idx)
                for loopback in loopbacks:
                    if default_out["name"] in loopback["name"]:
                        return loopback
        except OSError:
            pass

        return loopbacks[0]

    def _capture_with_soundcard(self) -> None:
        import soundcard as sc

        errors: list[str] = []
        mic = None

        try:
            speaker = sc.default_speaker()
            mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
            logger.info("Capturing loopback from default speaker: %s", speaker.name)
        except Exception as exc:
            errors.append(f"default speaker: {exc}")

        if mic is None:
            for speaker in sc.all_speakers():
                try:
                    mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
                    logger.info("Capturing loopback from speaker: %s", speaker.name)
                    break
                except Exception as exc:
                    errors.append(f"{speaker.name}: {exc}")

        if mic is None:
            loopback_mics = [
                m
                for m in sc.all_microphones(include_loopback=True)
                if "loopback" in m.name.lower()
            ]
            if loopback_mics:
                mic = loopback_mics[0]
                logger.info("Using loopback microphone: %s", mic.name)

        if mic is None:
            raise RuntimeError(
                "No loopback audio device found. " + "; ".join(errors[:3])
            )

        with mic.recorder(
            samplerate=SAMPLE_RATE, channels=CHANNELS, blocksize=FRAME_SAMPLES
        ) as recorder:
            LoopbackAudioTrack.capture_state = "live"
            LoopbackAudioTrack.capture_error = None
            while not self._stop_event.is_set():
                data = recorder.record(numframes=FRAME_SAMPLES)
                if data is None:
                    continue
                frame = np.asarray(data, dtype=np.float32)
                if frame.ndim == 1:
                    frame = np.column_stack([frame, frame])
                elif frame.shape[1] == 1:
                    frame = np.column_stack([frame[:, 0], frame[:, 0]])
                elif frame.shape[1] > 2:
                    frame = frame[:, :2]

                try:
                    self._queue.put(frame, timeout=0.5)
                except queue.Full:
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self._queue.put_nowait(frame)
                    except queue.Full:
                        pass

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if sys.platform == "win32" and _capture_mode == "virtual":
                    self._capture_with_virtual_cable()
                elif sys.platform == "win32":
                    self._capture_with_pyaudiowpatch()
                else:
                    self._capture_with_soundcard()
            except Exception as exc:
                if not self._stop_event.is_set():
                    self._log_capture_error(str(exc))
                    time.sleep(2)

    async def recv(self) -> av.AudioFrame:
        if self.readyState != "live":
            raise Exception("Track is not live")

        if self._start_time is None:
            self._start_time = time.time()
            self._pts = 0
        else:
            target = self._start_time + (self._pts / SAMPLE_RATE)
            wait = target - time.time()
            if wait > 0:
                await asyncio.sleep(wait)

        loop = asyncio.get_event_loop()
        try:
            samples = await loop.run_in_executor(
                None, lambda: self._queue.get(timeout=1.0)
            )
        except queue.Empty:
            samples = np.zeros((FRAME_SAMPLES, CHANNELS), dtype=np.float32)

        pcm = np.clip(samples, -1.0, 1.0)
        LoopbackAudioTrack.audio_level = float(np.sqrt(np.mean(pcm * pcm)))
        pcm_s16 = (pcm * 32767.0).astype(np.int16)
        interleaved = np.ascontiguousarray(pcm_s16.reshape(1, -1))

        frame = av.AudioFrame.from_ndarray(interleaved, format="s16", layout="stereo")
        frame.sample_rate = SAMPLE_RATE
        frame.pts = self._pts
        frame.time_base = TIME_BASE
        self._pts += FRAME_SAMPLES
        return frame

    def stop(self) -> None:
        super().stop()
        self._stop_event.set()


def probe_audio_devices(mode: str = "virtual") -> dict:
    """Check whether audio capture is ready for the selected mode."""
    if sys.platform != "win32":
        return {"ok": True, "message": "Non-Windows platform", "mode": mode}

    if mode == "virtual":
        from server.virtual_speaker import find_virtual_cable_devices

        import pyaudiowpatch as pyaudio

        pa = pyaudio.PyAudio()
        try:
            devices = find_virtual_cable_devices(pa)
            if devices is None:
                return {
                    "ok": False,
                    "mode": "virtual",
                    "message": (
                        "Install the free VB-Audio Virtual Cable once on this PC, "
                        "then restart SoundShare."
                    ),
                }
            return {
                "ok": True,
                "mode": "virtual",
                "message": f"Ready: {devices.output_name}",
                "output": devices.output_name,
                "input": devices.loopback_name,
            }
        finally:
            pa.terminate()

    try:
        import pyaudiowpatch as pyaudio

        pa = pyaudio.PyAudio()
        try:
            device_count = pa.get_device_count()
            loopbacks = list(pa.get_loopback_device_info_generator())
            if loopbacks:
                device = pa.get_default_wasapi_loopback()
                return {
                    "ok": True,
                    "mode": "loopback",
                    "message": f"Ready: {device['name']}",
                    "device": device["name"],
                }
            return {
                "ok": False,
                "mode": "loopback",
                "message": (
                    "No speaker/headphones detected by Windows. "
                    "Use virtual speaker mode (default) or install VB-Cable."
                ),
                "device_count": device_count,
            }
        finally:
            pa.terminate()
    except Exception as exc:
        return {"ok": False, "mode": mode, "message": str(exc)}


_source_track: LoopbackAudioTrack | None = None
_relay = MediaRelay()


def get_relayed_track() -> MediaStreamTrack:
    global _source_track
    if _source_track is None:
        _source_track = LoopbackAudioTrack()
    return _relay.subscribe(_source_track)


def get_capture_status() -> dict:
    return {
        "state": LoopbackAudioTrack.capture_state,
        "error": LoopbackAudioTrack.capture_error,
        "level": round(LoopbackAudioTrack.audio_level, 4),
        "mode": _capture_mode,
    }


def shutdown_audio() -> None:
    global _source_track
    if _source_track is not None:
        _source_track.stop()
        _source_track = None
    LoopbackAudioTrack.capture_state = "stopped"
    LoopbackAudioTrack.capture_error = None
