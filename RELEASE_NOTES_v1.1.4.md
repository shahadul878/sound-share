## SoundShare v1.1.4

Fixes device connection, Windows Firewall for WebRTC audio, and a startup bug in v1.1.3.

### Download

**`SoundShare-Setup-1.1.4.exe`** — single-file Windows installer

### What's fixed

- **Devices not connecting** — firewall now allows SoundShare.exe for WebRTC media (UDP), not just TCP port 8765
- **App not opening** — fixed single-instance check that caused immediate exit on launch (v1.1.3 regression)
- **Duplicate instances** — only one SoundShare window can run at a time
- **Clearer errors** — listener page shows a firewall hint when WebRTC fails
- Includes v1.1.2 config-in-AppData fix and host dashboard from v1.1.1

### Quick start

1. Download and run **`SoundShare-Setup-1.1.4.exe`** as Administrator
2. Launch **SoundShare** from Desktop — host dashboard opens automatically
3. Share the **Network URL** with phones on the same Wi-Fi
4. Tap **Connect & Play** on each device

### Troubleshooting

- If devices stay on "Connecting", allow SoundShare through Windows Firewall (Private network)
- Close extra SoundShare windows in Task Manager before launching again
