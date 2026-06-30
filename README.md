# SoundShare

**Stream PC audio to any device on your network — no listener app required.**

Developed by **H M Shahadul Islam**

---

## For end users (Windows installer)

1. Run **`SoundShare-Setup-1.0.0.exe`** (from `dist/` after building, or from release)
2. Complete the installer — VB-Audio Virtual Cable is included automatically
3. Launch **SoundShare** from Desktop
4. Share the **Network** URL with phones on your Wi-Fi
5. Listeners tap **Connect & Play**

No Python, no extra plugins, no manual sound configuration.

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
- `dist/SoundShare.exe` — portable
- `dist/SoundShare-Setup-1.0.0.exe` — full installer with VB-Cable

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
```

---

## License

Copyright (c) 2026 H M Shahadul Islam. VB-Audio Virtual Cable subject to vb-audio.com terms.
