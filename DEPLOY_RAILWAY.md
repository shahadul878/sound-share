# Deploy SoundShare on Railway

SoundShare can run on [Railway](https://railway.com) as a public web + WebRTC server. This is useful for demos, remote listener URLs, and testing connectivity over the internet.

## Important limitation

**Railway cannot capture your Windows PC audio.** Cloud containers have no access to your desktop sound card or VB-Cable.

| Deployment | Best for |
|------------|----------|
| **Windows installer** (`SoundShare-Setup-1.1.4.exe`) | Real PC audio → phones on your Wi-Fi |
| **Railway (cloud)** | Public URL, WebRTC demo, silent stream test |

For production PC audio streaming, use the **Windows desktop app** on the machine that plays the sound.

---

## One-click deploy (GitHub)

1. Push this repo to GitHub (`shahadul878/sound-share`).
2. Go to [railway.com/new](https://railway.com/new) → **Deploy from GitHub repo**.
3. Select the **sound-share** repository.
4. Railway detects the `Dockerfile` automatically.
5. Under **Settings → Networking**, click **Generate Domain** (e.g. `soundshare-production.up.railway.app`).
6. Deploy and open `https://your-domain.up.railway.app/host`.

---

## Environment variables

Set these in Railway → **Variables**:

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | Auto | Set by Railway — do not override |
| `SOUNDSHARE_OWNER_TOKEN` | Recommended | Fixed token for remote owner panel access |
| `SOUNDSHARE_LISTENER_PASSWORD` | Optional | Require password for listeners |
| `SOUNDSHARE_SILENT` | Default `1` via cloud | `1` = silent audio (default on Railway) |
| `SOUNDSHARE_ICE_SERVERS` | Optional | JSON array of STUN/TURN servers for WebRTC |
| `SOUNDSHARE_DATA_DIR` | Optional | Config path (default `/data`) |

Example `SOUNDSHARE_ICE_SERVERS` (with TURN for strict NAT):

```json
[{"urls":"stun:stun.l.google.com:19302"},{"urls":"turn:your-turn.example.com:3478","username":"user","credential":"pass"}]
```

---

## Persistent config (optional)

Attach a Railway **Volume** mounted at `/data` so owner token and block lists survive redeploys.

---

## Health check

Railway uses `GET /health` → `{"status":"ok","service":"soundshare"}`.

---

## Local Docker test

```bash
cd soundshare
docker build -t soundshare .
docker run --rm -p 8765:8765 -e PORT=8765 -e SOUNDSHARE_CLOUD=1 soundshare
```

Open http://127.0.0.1:8765/host

---

## CLI deploy

```bash
npm i -g @railway/cli
railway login
cd soundshare
railway init
railway up
railway domain
```

---

## After deploy

- **Listeners:** `https://your-domain.up.railway.app/`
- **Host dashboard:** `https://your-domain.up.railway.app/host`
- **Owner panel:** `https://your-domain.up.railway.app/panel` (use `SOUNDSHARE_OWNER_TOKEN` header when not on localhost)

Developed by **H M Shahadul Islam**
