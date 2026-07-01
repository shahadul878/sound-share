const CLIENT_ID_KEY = "soundshare_client_id";
const LISTENER_TOKEN_KEY = "soundshare_listener_token";
const DEVICE_NAME_KEY = "soundshare_device_name";

const connectBtn = document.getElementById("connectBtn");
const muteBtn = document.getElementById("muteBtn");
const volumeSlider = document.getElementById("volume");
const statusBadge = document.getElementById("statusBadge");
const listenerCount = document.getElementById("listenerCount");
const connectionStateEl = document.getElementById("connectionState");
const captureStatusEl = document.getElementById("captureStatus");
const audioMeterEl = document.getElementById("audioMeter");
const meterFillEl = document.getElementById("meterFill");
const meterLabelEl = document.getElementById("meterLabel");
const player = document.getElementById("player");
const authGate = document.getElementById("authGate");
const listenerMain = document.getElementById("listenerMain");
const listenerPasswordInput = document.getElementById("listenerPasswordInput");
const authBtn = document.getElementById("authBtn");
const authError = document.getElementById("authError");
const deviceNameInput = document.getElementById("deviceName");

let pc = null;
let statusTimer = null;
let audioContext = null;
let passwordRequired = false;

function getClientId() {
  let id = localStorage.getItem(CLIENT_ID_KEY);
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : "dev-" + Date.now();
    localStorage.setItem(CLIENT_ID_KEY, id);
  }
  return id;
}

function getListenerToken() {
  return sessionStorage.getItem(LISTENER_TOKEN_KEY);
}

function setListenerToken(token) {
  sessionStorage.setItem(LISTENER_TOKEN_KEY, token);
}

function getDeviceName() {
  const saved = localStorage.getItem(DEVICE_NAME_KEY);
  if (saved) return saved;
  const ua = navigator.userAgent || "";
  if (/iPhone/i.test(ua)) return "iPhone";
  if (/iPad/i.test(ua)) return "iPad";
  if (/Android/i.test(ua)) return "Android";
  if (/Windows/i.test(ua)) return "Windows PC";
  if (/Mac/i.test(ua)) return "Mac";
  return "Listener";
}

deviceNameInput.value = getDeviceName();
deviceNameInput.addEventListener("change", () => {
  localStorage.setItem(DEVICE_NAME_KEY, deviceNameInput.value.trim() || getDeviceName());
});

function setStatus(state, label) {
  statusBadge.className = `status-badge ${state}`;
  statusBadge.textContent = label;
}

function setConnectionState(text) {
  connectionStateEl.textContent = text;
}

function showAuthGate() {
  authGate.classList.remove("hidden");
  listenerMain.classList.add("hidden");
}

function showListenerMain() {
  authGate.classList.add("hidden");
  listenerMain.classList.remove("hidden");
}

async function checkAuth() {
  try {
    const res = await fetch("/api/auth/status");
    const data = await res.json();
    passwordRequired = data.password_required;

    if (!passwordRequired) {
      showListenerMain();
      return;
    }

    if (getListenerToken()) {
      showListenerMain();
      return;
    }

    showAuthGate();
  } catch {
    showListenerMain();
  }
}

async function unlockWithPassword() {
  const password = listenerPasswordInput.value;
  authError.classList.add("hidden");

  try {
    const res = await fetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    const data = await res.json();
    if (!res.ok) {
      authError.textContent = data.error || "Wrong password";
      authError.classList.remove("hidden");
      return;
    }

    setListenerToken(data.token);
    showListenerMain();
    connect();
  } catch {
    authError.textContent = "Could not verify password";
    authError.classList.remove("hidden");
  }
}

authBtn.addEventListener("click", unlockWithPassword);
listenerPasswordInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") unlockWithPassword();
});

async function fetchStatus() {
  try {
    const res = await fetch("/status");
    if (!res.ok) return;
    const data = await res.json();
    listenerCount.textContent = `Listeners: ${data.listeners}`;

    if (data.capture === "live") {
      captureStatusEl.classList.add("hidden");
      captureStatusEl.textContent = "";
      audioMeterEl.classList.remove("hidden");
      const pct = Math.min(100, Math.round((data.audio_level || 0) * 200));
      meterFillEl.style.width = pct + "%";
      meterLabelEl.textContent = pct > 2 ? "Receiving" : "Silent";
      if (pc && pc.connectionState === "connected" && pct < 2) {
        captureStatusEl.classList.remove("hidden");
        captureStatusEl.textContent =
          "Connected but no PC audio detected. Play something on the PC (YouTube, music).";
      }
    } else if (data.capture_error) {
      audioMeterEl.classList.add("hidden");
      captureStatusEl.classList.remove("hidden");
      captureStatusEl.textContent =
        "PC is not capturing audio: " + data.capture_error;
    }
  } catch {
  }
}

function startStatusPolling() {
  fetchStatus();
  if (statusTimer) clearInterval(statusTimer);
  statusTimer = setInterval(fetchStatus, 3000);
}

fetchStatus();
setInterval(fetchStatus, 5000);

function stopStatusPolling() {
  if (statusTimer) {
    clearInterval(statusTimer);
    statusTimer = null;
  }
}

function waitForIceGathering(peerConnection) {
  if (peerConnection.iceGatheringState === "complete") {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    function checkState() {
      if (peerConnection.iceGatheringState === "complete") {
        peerConnection.removeEventListener("icegatheringstatechange", checkState);
        resolve();
      }
    }
    peerConnection.addEventListener("icegatheringstatechange", checkState);
    setTimeout(resolve, 5000);
  });
}

async function startPlayback(stream) {
  player.srcObject = stream;
  player.volume = Number(volumeSlider.value) / 100;
  player.muted = false;

  try {
    await player.play();
    return;
  } catch {
    // Mobile browsers often block <audio>.play(); Web Audio API works better.
  }

  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return;

  if (!audioContext) {
    audioContext = new AudioCtx();
  }
  if (audioContext.state === "suspended") {
    await audioContext.resume();
  }

  const source = audioContext.createMediaStreamSource(stream);
  source.connect(audioContext.destination);
}

function attachRemoteTrack(event) {
  const stream =
    event.streams && event.streams[0]
      ? event.streams[0]
      : new MediaStream([event.track]);
  return startPlayback(stream);
}

async function disconnect() {
  if (pc) {
    pc.close();
    pc = null;
  }
  player.srcObject = null;
  if (audioContext) {
    await audioContext.close().catch(() => {});
    audioContext = null;
  }
  connectBtn.disabled = false;
  connectBtn.textContent = "Connect & Play";
  setStatus("idle", "Idle");
  setConnectionState("Not connected");
  listenerCount.textContent = "Listeners: —";
  stopStatusPolling();
}

async function connect() {
  if (passwordRequired && !getListenerToken()) {
    showAuthGate();
    return;
  }

  connectBtn.disabled = true;
  setStatus("connecting", "Connecting...");
  setConnectionState("Negotiating...");

  const deviceName = deviceNameInput.value.trim() || getDeviceName();
  localStorage.setItem(DEVICE_NAME_KEY, deviceName);

  try {
    pc = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });

    pc.addTransceiver("audio", { direction: "recvonly" });

    pc.ontrack = (event) => {
      attachRemoteTrack(event).catch((err) => {
        console.error("Playback failed:", err);
        setConnectionState("Audio playback blocked - tap Connect again");
      });
    };

    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      setConnectionState(state);

      if (state === "connected") {
        setStatus("live", "Live");
        connectBtn.textContent = "Disconnect";
        connectBtn.disabled = false;
        startStatusPolling();
        if (player.srcObject) {
          startPlayback(player.srcObject).catch(() => {});
        }
      } else if (state === "connecting") {
        setStatus("connecting", "Connecting...");
      } else if (state === "failed") {
        setStatus("error", "Connection failed");
        setConnectionState(
          "WebRTC failed — allow SoundShare in Windows Firewall (Private network) and try again"
        );
        connectBtn.textContent = "Connect & Play";
        connectBtn.disabled = false;
        stopStatusPolling();
      } else if (state === "disconnected" || state === "closed") {
        setStatus("error", "Disconnected");
        connectBtn.textContent = "Connect & Play";
        connectBtn.disabled = false;
        stopStatusPolling();
      }
    };

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await waitForIceGathering(pc);

    const headers = { "Content-Type": "application/json" };
    const token = getListenerToken();
    if (token) headers["X-Listener-Token"] = token;

    const response = await fetch("/offer", {
      method: "POST",
      headers,
      body: JSON.stringify({
        sdp: pc.localDescription.sdp,
        type: pc.localDescription.type,
        client_id: getClientId(),
        device_name: deviceName,
        listener_token: token,
      }),
    });

    if (response.status === 401) {
      sessionStorage.removeItem(LISTENER_TOKEN_KEY);
      showAuthGate();
      throw new Error("Password required");
    }

    if (response.status === 403) {
      throw new Error("This device was blocked by the owner");
    }

    if (!response.ok) {
      throw new Error(`Signaling failed (${response.status})`);
    }

    const answer = await response.json();
    await pc.setRemoteDescription(answer);
  } catch (err) {
    console.error(err);
    setStatus("error", "Connection failed");
    setConnectionState(err.message || "Error");
    connectBtn.disabled = false;
    connectBtn.textContent = "Connect & Play";
    if (pc) {
      pc.close();
      pc = null;
    }
  }
}

connectBtn.addEventListener("click", () => {
  if (pc && (pc.connectionState === "connected" || pc.connectionState === "connecting")) {
    disconnect();
  } else {
    connect();
  }
});

volumeSlider.addEventListener("input", () => {
  player.volume = Number(volumeSlider.value) / 100;
  if (player.volume > 0) {
    player.muted = false;
    muteBtn.setAttribute("aria-pressed", "false");
    muteBtn.textContent = "Mute";
  }
});

muteBtn.addEventListener("click", () => {
  const muted = !player.muted;
  player.muted = muted;
  muteBtn.setAttribute("aria-pressed", String(muted));
  muteBtn.textContent = muted ? "Unmute" : "Mute";
});

player.volume = 1;
checkAuth();
