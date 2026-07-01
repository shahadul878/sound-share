const OWNER_TOKEN_KEY = "soundshare_owner_token";
const POLL_MS = 2500;

const loginSection = document.getElementById("loginSection");
const dashboardSection = document.getElementById("dashboardSection");
const ownerTokenInput = document.getElementById("ownerTokenInput");
const loginBtn = document.getElementById("loginBtn");
const loginError = document.getElementById("loginError");

const statListeners = document.getElementById("statListeners");
const statDevices = document.getElementById("statDevices");
const statBlocked = document.getElementById("statBlocked");
const deviceList = document.getElementById("deviceList");
const blockedList = document.getElementById("blockedList");
const passwordToggle = document.getElementById("passwordToggle");
const passwordFields = document.getElementById("passwordFields");
const listenerPassword = document.getElementById("listenerPassword");
const saveSecurityBtn = document.getElementById("saveSecurityBtn");
const securityMsg = document.getElementById("securityMsg");
const ownerTokenDisplay = document.getElementById("ownerTokenDisplay");
const copyTokenBtn = document.getElementById("copyTokenBtn");
const regenTokenBtn = document.getElementById("regenTokenBtn");
const refreshBtn = document.getElementById("refreshBtn");

let pollTimer = null;

function getOwnerToken() {
  return sessionStorage.getItem(OWNER_TOKEN_KEY) || "";
}

function setOwnerToken(token) {
  sessionStorage.setItem(OWNER_TOKEN_KEY, token);
}

function ownerHeaders() {
  return {
    "Content-Type": "application/json",
    "X-Owner-Token": getOwnerToken(),
  };
}

function showLogin() {
  loginSection.classList.remove("hidden");
  dashboardSection.classList.add("hidden");
  stopPolling();
}

function showDashboard() {
  loginSection.classList.add("hidden");
  dashboardSection.classList.remove("hidden");
  refreshAll();
  startPolling();
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(refreshDevices, POLL_MS);
}

function formatDuration(sec) {
  if (sec < 60) return sec + "s";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m < 60) return m + "m " + s + "s";
  return Math.floor(m / 60) + "h " + (m % 60) + "m";
}

function stateBadge(state) {
  const cls =
    state === "connected" ? "badge-live" : state === "connecting" ? "badge-connecting" : "badge-idle";
  return `<span class="device-badge ${cls}">${state}</span>`;
}

function renderDevices(devices) {
  if (!devices.length) {
    deviceList.innerHTML = '<p class="empty-state">No devices connected</p>';
    return;
  }

  deviceList.innerHTML = devices
    .map(
      (d) => `
    <div class="device-item" data-peer-id="${d.peer_id}">
      <div class="device-info">
        <div class="device-name">${escapeHtml(d.device_name)}</div>
        <div class="device-meta">
          ${stateBadge(d.state)}
          <span>${escapeHtml(d.ip)}</span>
          <span>${formatDuration(d.connected_for_sec)}</span>
        </div>
        <div class="device-ua">${escapeHtml(shortUa(d.user_agent))}</div>
      </div>
      <div class="device-actions">
        <button class="secondary-btn btn-sm" data-action="kick" data-peer-id="${d.peer_id}">Remove</button>
        <button class="danger-btn btn-sm" data-action="block" data-peer-id="${d.peer_id}">Block</button>
      </div>
    </div>`
    )
    .join("");
}

function renderBlocked(ids) {
  if (!ids.length) {
    blockedList.innerHTML = '<p class="empty-state">No blocked devices</p>';
    return;
  }

  blockedList.innerHTML = ids
    .map(
      (id) => `
    <div class="device-item">
      <div class="device-info">
        <div class="device-name">${escapeHtml(id.slice(0, 16))}…</div>
        <div class="device-meta"><span class="device-badge badge-blocked">Blocked</span></div>
      </div>
      <div class="device-actions">
        <button class="secondary-btn btn-sm" data-action="unblock" data-client-id="${escapeHtml(id)}">Unblock</button>
      </div>
    </div>`
    )
    .join("");
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function shortUa(ua) {
  if (!ua) return "Unknown browser";
  if (ua.length <= 60) return ua;
  return ua.slice(0, 57) + "…";
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { ...ownerHeaders(), ...(options.headers || {}) },
  });
  if (res.status === 401) {
    showLogin();
    throw new Error("Unauthorized");
  }
  return res;
}

async function refreshSettings() {
  const res = await api("/api/panel/settings");
  const data = await res.json();
  passwordToggle.checked = data.password_required;
  passwordFields.classList.toggle("hidden", !data.password_required);
  ownerTokenDisplay.textContent = data.owner_token || "—";
  statBlocked.textContent = data.blocked_count || 0;
}

async function refreshDevices() {
  const res = await api("/api/panel/devices");
  const data = await res.json();
  statListeners.textContent = data.listeners;
  statDevices.textContent = data.devices.length;
  renderDevices(data.devices);
  renderBlocked(data.blocked_client_ids || []);
  statBlocked.textContent = (data.blocked_client_ids || []).length;
}

async function refreshAll() {
  try {
    await refreshSettings();
    await refreshDevices();
  } catch (err) {
    console.error(err);
  }
}

async function tryLogin() {
  const token = ownerTokenInput.value.trim();
  if (!token) {
    loginError.textContent = "Enter your owner token";
    loginError.classList.remove("hidden");
    return;
  }

  setOwnerToken(token);
  try {
    const res = await api("/api/panel/settings");
    if (!res.ok) throw new Error("Invalid token");
    loginError.classList.add("hidden");
    showDashboard();
  } catch {
    sessionStorage.removeItem(OWNER_TOKEN_KEY);
    loginError.textContent = "Invalid owner token";
    loginError.classList.remove("hidden");
  }
}

async function saveSecurity() {
  const body = {
    password_enabled: passwordToggle.checked,
  };
  if (passwordToggle.checked && listenerPassword.value.trim()) {
    body.password = listenerPassword.value.trim();
  }

  const res = await api("/api/panel/settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });

  const data = await res.json();
  if (!res.ok) {
    securityMsg.textContent = data.error || "Failed to save";
    securityMsg.className = "form-error";
    securityMsg.classList.remove("hidden");
    return;
  }

  securityMsg.textContent = data.password_required
    ? "Password protection enabled"
    : "Open access — no password required";
  securityMsg.className = "form-success";
  securityMsg.classList.remove("hidden");
  passwordFields.classList.toggle("hidden", !data.password_required);
  ownerTokenDisplay.textContent = data.owner_token;
  setTimeout(() => securityMsg.classList.add("hidden"), 3000);
}

async function deviceAction(action, peerId) {
  const res = await api(`/api/panel/devices/${peerId}/${action}`, { method: "POST" });
  if (res.ok) await refreshDevices();
}

async function unblockAction(clientId) {
  const res = await api(`/api/panel/blocked/${encodeURIComponent(clientId)}/unblock`, {
    method: "POST",
  });
  if (res.ok) await refreshDevices();
}

passwordToggle.addEventListener("change", () => {
  passwordFields.classList.toggle("hidden", !passwordToggle.checked);
});

loginBtn.addEventListener("click", tryLogin);
ownerTokenInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") tryLogin();
});

saveSecurityBtn.addEventListener("click", saveSecurity);
refreshBtn.addEventListener("click", refreshAll);

copyTokenBtn.addEventListener("click", () => {
  const text = ownerTokenDisplay.textContent;
  if (text && text !== "—") {
    navigator.clipboard.writeText(text).catch(() => {});
    copyTokenBtn.textContent = "Copied!";
    setTimeout(() => (copyTokenBtn.textContent = "Copy"), 2000);
  }
});

regenTokenBtn.addEventListener("click", async () => {
  if (!confirm("Regenerate owner token? You will need the new token to access this panel.")) return;
  const res = await api("/api/panel/settings", {
    method: "PUT",
    body: JSON.stringify({ regenerate_owner_token: true }),
  });
  const data = await res.json();
  if (res.ok) {
    setOwnerToken(data.owner_token);
    ownerTokenDisplay.textContent = data.owner_token;
  }
});

deviceList.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  const { action, peerId } = btn.dataset;
  if (action === "kick" || action === "block") deviceAction(action, peerId);
});

blockedList.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-action=unblock]");
  if (!btn) return;
  unblockAction(btn.dataset.clientId);
});

// Init — localhost panel access works without token (server-side)
async function initPanel() {
  try {
    const res = await fetch("/api/panel/settings");
    if (res.ok) {
      const data = await res.json();
      if (data.owner_token) setOwnerToken(data.owner_token);
      showDashboard();
      return;
    }
  } catch {
    // fall through to login
  }

  if (getOwnerToken()) {
    try {
      const res = await api("/api/panel/settings");
      if (res.ok) {
        showDashboard();
        return;
      }
    } catch {
      // fall through
    }
  }

  showLogin();
  loginSection.classList.remove("hidden");
}

initPanel();
