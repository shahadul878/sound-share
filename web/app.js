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

let pc = null;
let statusTimer = null;
let audioContext = null;

function setStatus(state, label) {
  statusBadge.className = `status-badge ${state}`;
  statusBadge.textContent = label;
}

function setConnectionState(text) {
  connectionStateEl.textContent = text;
}

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
  connectBtn.disabled = true;
  setStatus("connecting", "Connecting...");
  setConnectionState("Negotiating...");

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
      } else if (state === "failed" || state === "disconnected" || state === "closed") {
        setStatus("error", "Disconnected");
        connectBtn.textContent = "Connect & Play";
        connectBtn.disabled = false;
        stopStatusPolling();
      }
    };

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await waitForIceGathering(pc);

    const response = await fetch("/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sdp: pc.localDescription.sdp,
        type: pc.localDescription.type,
      }),
    });

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
