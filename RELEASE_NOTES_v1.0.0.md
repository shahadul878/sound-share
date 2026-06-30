## SoundShare v1.0.0

Stream PC audio to any phone, tablet, or computer on your local network. Listeners open a link in their browser — no app install required.

**Developer:** H M Shahadul Islam

### Download (recommended)

**`SoundShare-Setup-1.0.0.exe`** — single-file Windows installer (~67 MB)

Everything in one click:
- SoundShare application
- Full VB-Audio Virtual Cable driver pack (bundled)
- Silent driver install during setup
- Desktop shortcut + firewall rule

### Quick start (Windows)

1. Download **`SoundShare-Setup-1.0.0.exe`**
2. Run as **Administrator**
3. Complete the install wizard
4. Launch **SoundShare** from Desktop
5. Share the **Network** URL with devices on your Wi-Fi
6. Listeners tap **Connect & Play**

### Highlights

- Low-latency WebRTC audio streaming to multiple listeners
- Virtual speaker — works without physical speakers
- No Python or extra plugins required for end users
- Redesigned listener UI with volume control and audio meter

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
