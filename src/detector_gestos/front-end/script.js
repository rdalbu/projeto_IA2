const video = document.getElementById('cameraVideo');
const fallback = document.getElementById('fallback');
const statusDot = document.getElementById('statusDot');
const camLabel = document.getElementById('camLabel');
const toggle = document.getElementById('toggleSwitch');
const switchState = document.getElementById('switchState');

let stream = null;

// === CÂMERA ===
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false,
    });
    video.srcObject = stream;
    fallback.style.display = 'none';
    statusDot.classList.replace('status-off', 'status-on');
    camLabel.textContent = 'Ativa';
  } catch (err) {
    console.error('Erro ao acessar câmera:', err);
    fallback.style.display = 'flex';
    statusDot.classList.replace('status-on', 'status-off');
    camLabel.textContent = 'Indisponível';
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  video.srcObject = null;
  fallback.style.display = 'flex';
  statusDot.classList.replace('status-on', 'status-off');
  camLabel.textContent = 'Desativada';
}

function setSwitch(on) {
  toggle.setAttribute('aria-checked', on ? 'true' : 'false');
  switchState.textContent = on ? 'ATIVADO' : 'DESATIVADO';
  on ? startCamera() : stopCamera();
}

toggle.addEventListener('click', () => {
  const isOn = toggle.getAttribute('aria-checked') === 'true';
  setSwitch(!isOn);
});

// === PLAYER ===
const musicPlayer = document.getElementById('musicPlayer');
const playPauseBtn = document.getElementById('playPauseBtn');
const seekBar = document.getElementById('seekBar');
const timeLabel = document.getElementById('timeLabel');

let playing = false;

playPauseBtn.addEventListener('click', () => {
  if (playing) {
    musicPlayer.pause();
    playPauseBtn.textContent = '▶️';
  } else {
    musicPlayer.play();
    playPauseBtn.textContent = '⏸️';
  }
  playing = !playing;
});

musicPlayer.addEventListener('timeupdate', () => {
  seekBar.value = (musicPlayer.currentTime / musicPlayer.duration) * 100 || 0;
  const mins = Math.floor(musicPlayer.currentTime / 60)
    .toString()
    .padStart(2, '0');
  const secs = Math.floor(musicPlayer.currentTime % 60)
    .toString()
    .padStart(2, '0');
  timeLabel.textContent = `${mins}:${secs}`;
});

seekBar.addEventListener('input', () => {
  musicPlayer.currentTime = (seekBar.value / 100) * musicPlayer.duration;
});

// === MICROFONE ===
const micToggle = document.getElementById('micToggleSwitch');
const micSwitchState = document.getElementById('micSwitchState');

let micStream = null;

async function startMic() {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false,
    });
    micSwitchState.textContent = 'ATIVADO';
    micToggle.setAttribute('aria-checked', 'true');
  } catch (err) {
    console.error('Erro ao acessar microfone:', err);
    micSwitchState.textContent = 'Indisponível';
    micToggle.setAttribute('aria-checked', 'false');
  }
}

function stopMic() {
  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
    micStream = null;
  }
  micSwitchState.textContent = 'DESATIVADO';
  micToggle.setAttribute('aria-checked', 'false');
}

micToggle.addEventListener('click', () => {
  const isOn = micToggle.getAttribute('aria-checked') === 'true';
  if (isOn) {
    stopMic();
  } else {
    startMic();
  }
});
