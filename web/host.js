const statListeners = document.getElementById("statListeners");
const statCapture = document.getElementById("statCapture");
const statSecurity = document.getElementById("statSecurity");
const networkUrl = document.getElementById("networkUrl");
const copyUrlBtn = document.getElementById("copyUrlBtn");
const qrBox = document.getElementById("qrBox");
const qrImage = document.getElementById("qrImage");
const captureWarning = document.getElementById("captureWarning");

async function refresh() {
  try {
    const res = await fetch("/api/host/info");
    if (!res.ok) return;
    const data = await res.json();

    statListeners.textContent = data.listeners;
    statCapture.textContent = data.capture === "live" ? "Live" : "Waiting";
    statSecurity.textContent = data.password_required ? "Password" : "Open";

    const url = data.network_url;
    networkUrl.textContent = url;

    if (url && url !== "Loading…") {
      qrImage.src =
        "https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=" +
        encodeURIComponent(url);
      qrBox.classList.remove("hidden");
    }

    if (data.capture_error) {
      captureWarning.textContent = "Audio issue: " + data.capture_error;
      captureWarning.classList.remove("hidden");
    } else if (data.capture !== "live") {
      captureWarning.textContent =
        "Audio capture starting… Play sound on this PC if listeners hear nothing.";
      captureWarning.classList.remove("hidden");
    } else {
      captureWarning.classList.add("hidden");
    }
  } catch (err) {
    console.error(err);
  }
}

copyUrlBtn.addEventListener("click", () => {
  const text = networkUrl.textContent;
  if (!text || text === "Loading…") return;
  navigator.clipboard.writeText(text).catch(() => {});
  copyUrlBtn.textContent = "Copied!";
  setTimeout(() => (copyUrlBtn.textContent = "Copy"), 2000);
});

refresh();
setInterval(refresh, 3000);
