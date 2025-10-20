const cameraImg = document.getElementById("cameraStream");
const fallback = document.getElementById("fallback");
const statusDot = document.getElementById("statusDot");
const camLabel = document.getElementById("camLabel");
const toggle = document.getElementById("toggleSwitch");
const switchState = document.getElementById("switchState");

// === CÂMERA (preview do backend via MJPEG) ===
function startPreview() {
  cameraImg.src = "/stream?ts=" + Date.now();
  cameraImg.onload = () => {
    fallback.style.display = "none";
    statusDot.classList.replace("status-off", "status-on");
    camLabel.textContent = "Ativa";
  };
  cameraImg.onerror = () => {
    fallback.style.display = "flex";
    statusDot.classList.replace("status-on", "status-off");
    camLabel.textContent = "Indisponível";
  };
}

function stopPreview() {
  cameraImg.removeAttribute('src');
  fallback.style.display = "flex";
  statusDot.classList.replace("status-on", "status-off");
  camLabel.textContent = "Desativada";
}

function setSwitch(on) {
  // Controla a pré-visualização MJPEG servida pelo backend.
  toggle.setAttribute("aria-checked", on ? "true" : "false");
  switchState.textContent = on ? "ATIVADO" : "DESATIVADO";
  on ? startPreview() : stopPreview();
}

// Auto iniciar preview na carga da página
try {
  document.addEventListener('DOMContentLoaded', () => {
    setSwitch(true);
  });
} catch {}

toggle.addEventListener("click", () => {
  const isOn = toggle.getAttribute("aria-checked") === "true";
  setSwitch(!isOn);
});

// === PLAYER ===
const musicPlayer = document.getElementById("musicPlayer");
const playPauseBtn = document.getElementById("playPauseBtn");
const seekBar = document.getElementById("seekBar");
const timeLabel = document.getElementById("timeLabel");

let playing = false;

playPauseBtn.addEventListener("click", () => {
  if (playing) {
    musicPlayer.pause();
    playPauseBtn.textContent = "▶️";
  } else {
    musicPlayer.play();
    playPauseBtn.textContent = "⏸️";
  }
  playing = !playing;
});

musicPlayer.addEventListener("timeupdate", () => {
  seekBar.value = (musicPlayer.currentTime / musicPlayer.duration) * 100 || 0;
  const mins = Math.floor(musicPlayer.currentTime / 60)
    .toString()
    .padStart(2, "0");
  const secs = Math.floor(musicPlayer.currentTime % 60)
    .toString()
    .padStart(2, "0");
  timeLabel.textContent = `${mins}:${secs}`;
});

seekBar.addEventListener("input", () => {
  musicPlayer.currentTime = (seekBar.value / 100) * musicPlayer.duration;
});

// === MICROFONE ===
const micToggle = document.getElementById("micToggleSwitch");
const micSwitchState = document.getElementById("micSwitchState");

let micStream = null;

async function startMic() {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false,
    });
    micSwitchState.textContent = "ATIVADO";
    micToggle.setAttribute("aria-checked", "true");
  } catch (err) {
    console.error("Erro ao acessar microfone:", err);
    micSwitchState.textContent = "Indisponível";
    micToggle.setAttribute("aria-checked", "false");
  }
}

function stopMic() {
  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
    micStream = null;
  }
  micSwitchState.textContent = "DESATIVADO";
  micToggle.setAttribute("aria-checked", "false");
}

micToggle.addEventListener("click", () => {
  const isOn = micToggle.getAttribute("aria-checked") === "true";
  if (isOn) {
    stopMic();
  } else {
    startMic();
  }
});
