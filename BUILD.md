# SoundShare Windows Installer — Build Guide

## What you get

Running the build produces:

- `dist/SoundShare.exe` — standalone portable app (no Python needed)
- `dist/SoundShare-Setup-1.0.0.exe` — professional installer that includes:
  - VB-Audio Virtual Cable (silent install)
  - SoundShare application
  - Desktop shortcut
  - Windows Firewall rule for port 8765
  - Start Menu entry

## Prerequisites (on build machine)

1. **Python 3.10+** with project dependencies:
   ```powershell
   cd soundshare
   py -m pip install -r requirements.txt -r requirements-build.txt
   ```

2. **Inno Setup 6** — [https://jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)
   - Add `C:\Program Files (x86)\Inno Setup 6` to PATH, or set `INNO_SETUP` env var

## Build (one command)

```powershell
cd soundshare
.\build\build.ps1
```

The script will:

1. Download `VBCABLE_Setup_x64.exe` from vb-audio.com (if not already in `vendor/`)
2. Build `SoundShare.exe` with PyInstaller
3. Compile `SoundShare-Setup-1.0.0.exe` with Inno Setup

## Output

```
soundshare/dist/
  SoundShare.exe                 # Portable executable (can zip and share)
  SoundShare-Complete/           # Full package (VB-Cable + installer scripts)
  SoundShare-Setup-1.0.0.exe     # Full installer (requires Inno Setup on build machine)
```

If Inno Setup is not installed, the build creates **`SoundShare-Complete/`** instead:
- `SoundShare.exe`
- `VBCABLE_Setup_x64.exe`
- `Install-SoundShare.bat` — double-click as Administrator
- `README.txt`, `ABOUT.txt`

Zip `SoundShare-Complete` and share with end users.

## End-user install

**Option A — Complete package (no Inno Setup needed on build machine)**

1. Zip and share `dist/SoundShare-Complete/`
2. User runs **`Install-SoundShare.bat`** as Administrator
3. Launch **SoundShare** from Desktop
4. Share the Network URL with phones on Wi-Fi

**Option B — Professional installer (requires Inno Setup to build)**

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. Re-run `.\build\build.ps1`
3. Distribute `dist/SoundShare-Setup-1.0.0.exe`

## Developer

**H M Shahadul Islam** — Senior WordPress Engineer

## VB-Audio license

VB-Audio Virtual Cable is included per vb-audio.com terms (donationware).
SoundShare bundles it for one-click setup. Credit: VB-Audio Software.
