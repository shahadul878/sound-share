# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SoundShare Windows executable."""

import sys
from pathlib import Path

block_cipher = None
app_root = Path(SPECPATH).parent

a = Analysis(
    [str(app_root / "launcher.py")],
    pathex=[str(app_root)],
    binaries=[],
    datas=[
        (str(app_root / "web"), "web"),
    ],
    hiddenimports=[
        "av",
        "av.audio",
        "aiortc",
        "aiortc.contrib.media",
        "aiohttp",
        "aioice",
        "pyee",
        "google_crc32c",
        "cryptography",
        "dns",
        "comtypes",
        "pycaw",
        "pycaw.pycaw",
        "pyaudiowpatch",
        "qrcode",
        "numpy",
        "server",
        "server.app",
        "server.audio",
        "server.paths",
        "server.virtual_speaker",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SoundShare",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
