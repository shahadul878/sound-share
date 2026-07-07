# SoundShare

**Stream PC audio to any device on your network — no listener app required.**

Developed by **H M Shahadul Islam**

---

## For end users (Windows installer)

1. Run **`SoundShare-Setup-1.1.4.exe`** — one file, everything included
2. Complete the wizard — VB-Audio Virtual Cable (full driver pack) installs automatically
3. Launch **SoundShare** from Desktop
4. Share the **Network** URL with phones on your Wi-Fi
5. Listeners tap **Connect & Play**

No Python, no extra downloads, no manual sound configuration.

### Cloud deploy (Railway)

For a public URL over the internet (demo / remote listeners), see **[DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md)**.  
PC audio capture requires the Windows installer above.

---

## For developers (run from source)

```bash
cd soundshare
py -m pip install -r requirements.txt
py launcher.py
```

Or double-click `run.bat`.

Default port: **8765**

---

## Build the installer package

See **[BUILD.md](BUILD.md)** for full instructions.

```powershell
cd soundshare
.\build\build.ps1
```

Produces:
- `dist/SoundShare-Setup-1.1.4.exe` — **single-file installer** (SoundShare + full VB-Cable driver pack)
- `dist/SoundShare.exe` — portable app only

To use your own VB-Cable driver pack folder:

```powershell
.\build\build.ps1 -VbCablePath "C:\Users\...\Downloads\VBCABLE_Driver_Pack45"
```

**Requirements:** Python 3.10+, Inno Setup 6

---

## Features

- Virtual speaker (works without physical speakers)
- Low-latency WebRTC audio
- Multiple simultaneous listeners
- QR code + network URL in console
- Professional Windows installer
- Mobile-friendly listener page

---

## About the developer

**H M Shahadul Islam** — Senior WordPress Engineer

Specializing in scalable backend architecture, custom plugin ecosystems, and high-availability infrastructure. 7+ years architecting enterprise solutions handling 100K+ concurrent users, mentoring distributed development teams, and contributing to the WordPress open-source ecosystem. Deep expertise in WordPress Core APIs, object-oriented plugin architecture, and LEMP stack optimization with focus on security hardening and performance engineering.

Open `/about` in the listener UI for more details.

---

## Options

```bash
py launcher.py --port 8765
py launcher.py --loopback    # use physical speakers instead of virtual cable
py launcher.py --password mysecret   # require listener password
py launcher.py --no-password         # disable password protection
```

### Owner panel

Open **`http://127.0.0.1:8765/host`** on the host PC (opens automatically on launch).

- View all connected devices in real time
- **Remove** — disconnect a listener
- **Block** — disconnect and prevent that device from reconnecting
- **Password** — enable/disable listener password protection
- Owner token is printed in the console at startup (required to access panel from other devices)

---

## License

Copyright (c) 2026 H M Shahadul Islam. VB-Audio Virtual Cable subject to vb-audio.com terms.
