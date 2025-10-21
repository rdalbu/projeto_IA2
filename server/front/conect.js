const API = 'http://127.0.0.1:8000';
let ws = null;

async function startIA() {
  await fetch(`${API}/start`);
  ws = new WebSocket('ws://127.0.0.1:8000/ws');
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const title = document.getElementById('songTitle');
    if (title) {
      const p = Math.round((data.prob || 0) * 100);
      title.textContent = `🎯 ${data.label || data.gesture} (${p}%) → ${data.action || ''}`;
    }
  };
}

async function stopIA() {
  await fetch(`${API}/stop`);
  if (ws) ws.close();
}

document.getElementById('toggleSwitch').addEventListener('click', (e) => {
  const wasOn = e.currentTarget.getAttribute('aria-checked') === 'true';
  if (!wasOn) startIA();
  else stopIA();
});

