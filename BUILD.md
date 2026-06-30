# SoundShare Windows Installer — Build Guide

## What you get

Running the build produces:

- `dist/SoundShare-Setup-1.1.0.exe` — **single-file installer** (~67 MB) containing:
  - SoundShare application
  - Full VB-Audio Virtual Cable driver pack (`VBCABLE_Driver_Pack45`)
  - Silent VB-Cable install during setup
  - Desktop shortcut
  - Windows Firewall rule for port 8765
- `dist/SoundShare.exe` — portable app only (no installer)

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
.\build\build.ps1 -VbCablePath "C:\Users\SEO-PC-027\Downloads\VBCABLE_Driver_Pack45"
```

Or place the extracted driver pack in `vendor\VBCABLE_Driver_Pack45\` and run:

```powershell
.\build\build.ps1
```

The script will:

1. Copy or download the full `VBCABLE_Driver_Pack45` folder into `vendor/`
2. Build `SoundShare.exe` with PyInstaller
3. Compile `SoundShare-Setup-1.1.0.exe` with Inno Setup (single file)

## Output

```
soundshare/dist/
  SoundShare-Setup-1.1.0.exe     # Single-file installer (recommended for end users)
  SoundShare.exe                   # Portable executable only
```

## End-user install

1. Run **`SoundShare-Setup-1.1.0.exe`** as Administrator
2. Follow the wizard (VB-Cable installs silently from bundled driver pack)
3. Launch **SoundShare** from Desktop
4. Share the Network URL with phones on Wi-Fi

## Developer

**H M Shahadul Islam** — Senior WordPress Engineer

## VB-Audio license

VB-Audio Virtual Cable is included per vb-audio.com terms (donationware).
SoundShare bundles it for one-click setup. Credit: VB-Audio Software.
