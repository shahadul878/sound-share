## SoundShare v1.1.0

Stream PC audio to any phone, tablet, or computer on your local network.

**Developer:** H M Shahadul Islam

### Download (recommended)

**`SoundShare-Setup-1.1.0.exe`** — single-file Windows installer (~67 MB)

Everything in one click: SoundShare app, full VB-Audio Virtual Cable driver pack, silent install, desktop shortcut, and firewall rule.

### What's new in v1.1.0

- **Owner panel** (`/panel`) — track connected devices in real time
- **Remove or block** listeners from the panel
- **Optional listener password** — open access by default, or require a password
- **Device names** — listeners can label their device (shown in the panel)
- **Owner token** — secure panel access (printed in console at startup)

### Quick start (Windows)

1. Download **`SoundShare-Setup-1.1.0.exe`**
2. Run as **Administrator**
3. Launch **SoundShare** — owner panel opens automatically
4. Share the **Network** URL with devices on your Wi-Fi
5. Listeners tap **Connect & Play**

### Owner panel

Open `http://127.0.0.1:8765/panel` on the host PC to manage listeners, set passwords, and block devices.

### Requirements

- Windows 10/11 (64-bit)
- Same Wi-Fi network for PC and listeners
- Administrator rights for first-time install

### Build from source

```powershell
git clone https://github.com/shahadul878/sound-share.git
cd sound-share
py -m pip install -r requirements.txt
py launcher.py
```

See [BUILD.md](BUILD.md) for the installer build pipeline.
