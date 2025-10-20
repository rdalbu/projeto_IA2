const API = "http://127.0.0.1:8000";
let ws = null;

function appendLog(evt) {
  const box = document.getElementById("gestureLog");
  if (!box) return;
  const ts = new Date((evt.ts || Date.now()) * 1000);
  const hh = ts.getHours().toString().padStart(2, '0');
  const mm = ts.getMinutes().toString().padStart(2, '0');
  const ss = ts.getSeconds().toString().padStart(2, '0');
  const p = Math.round((evt.prob || 0) * 100);
  const line = `[${hh}:${mm}:${ss}] ${evt.type?.toUpperCase()}: ${evt.label} (${p}%) -> ${evt.action}`;
  const div = document.createElement('div');
  div.textContent = line;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

async function startIA() {
  try {
    const r = await fetch(`${API}/start`);
    const j = await r.json().catch(()=>({}));
    setRunnerState(true);
  } catch {}
  ws = new WebSocket("ws://127.0.0.1:8000/ws");
  ws.onopen = () => setWsState(true);
  ws.onclose = () => setWsState(false);
  ws.onerror = () => setWsState(false);
  ws.onmessage = (event) => {
    const evt = JSON.parse(event.data);
    const title = document.getElementById("songTitle");
    if (title) {
      const p = Math.round((evt.prob || 0) * 100);
      title.textContent = `🎯 ${evt.label} (${p}%) → ${evt.action}`;
    }
    appendLog(evt);
  };
}

async function stopIA() {
  try { await fetch(`${API}/stop`); } catch {}
  if (ws) ws.close();
  setRunnerState(false);
}

// Integrar com o switch de câmera (evita conflito com script.js)
document.getElementById("toggleSwitch").addEventListener("click", async () => {
  try {
    if (!ws || ws.readyState !== 1) {
      await startIA();
    } else {
      await stopIA();
    }
  } catch (err) {
    console.warn('Falha ao alternar runner:', err);
  }
});

// Integrar com o switch de microfone (KWS)
document.getElementById("micToggleSwitch").addEventListener("click", async (e) => {
  const wasOn = e.currentTarget.getAttribute('aria-checked') === 'true';
  try {
    if (!ws) return; // precisa do /start ativo
    if (!wasOn) {
      await fetch(`${API}/kws/enable`, { method: 'POST' });
      e.currentTarget.setAttribute('aria-checked', 'true');
      document.getElementById('micSwitchState').textContent = 'ATIVADO';
    } else {
      await fetch(`${API}/kws/disable`, { method: 'POST' });
      e.currentTarget.setAttribute('aria-checked', 'false');
      document.getElementById('micSwitchState').textContent = 'DESATIVADO';
    }
  } catch (err) {
    console.warn('Falha ao alternar KWS:', err);
  }
});

// Sincronizar estado inicial dos switches
(async function syncInitialStates(){
  // KWS
  try {
    const state = await fetch(`${API}/kws/state`).then(r=>r.json());
    const mic = document.getElementById('micToggleSwitch');
    mic.setAttribute('aria-checked', state.enabled ? 'true' : 'false');
    document.getElementById('micSwitchState').textContent = state.enabled ? 'ATIVADO' : 'DESATIVADO';
  } catch {}

  // Runner + Overlay: só sincroniza overlay se o runner estiver rodando; caso contrário mantém marcado por padrão
  let running = false;
  try {
    const run = await fetch(`${API}/state`).then(r=>r.json());
    running = !!run.running;
    setRunnerState(running);
  } catch {}
  try {
    const chk = document.getElementById('overlayToggle');
    if (!chk) return;
    if (running) {
      const ov = await fetch(`${API}/overlay/state`).then(r=>r.json());
      chk.checked = !!ov.enabled;
    } else {
      // runner parado: manter como marcado por padrão
      chk.checked = true;
    }
  } catch {}
})();

function setWsState(on){
  const wsDot = document.getElementById('wsDot');
  const wsLabel = document.getElementById('wsLabel');
  if (!wsDot || !wsLabel) return;
  wsDot.classList.toggle('dot-ok', !!on);
  wsDot.classList.toggle('dot-off', !on);
  wsLabel.textContent = on ? 'WS: ON' : 'WS: OFF';
}

function setRunnerState(on){
  const rDot = document.getElementById('runnerDot');
  const rLabel = document.getElementById('runnerLabel');
  if (!rDot || !rLabel) return;
  rDot.classList.toggle('dot-ok', !!on);
  rDot.classList.toggle('dot-off', !on);
  rLabel.textContent = on ? 'IA: RODANDO' : 'IA: PARADA';
}

// Modo de saída: PC x ESP32
const outSwitch = document.getElementById('outToggleSwitch');
const outState = document.getElementById('outSwitchState');

async function syncOutputState(){
  try{
    const s = await fetch(`${API}/output/state`).then(r=>r.json());
    const toEsp = (s.mode === 'serial') && s.serial_available;
    outSwitch.setAttribute('aria-checked', toEsp ? 'true' : 'false');
    outState.textContent = toEsp ? 'ESP32' : 'PC';
  }catch{}
}

outSwitch.addEventListener('click', async () => {
  try{
    // consulta estado atual do backend
    const s = await fetch(`${API}/output/state`).then(r=>r.json());
    const isEsp = outSwitch.getAttribute('aria-checked') === 'true';
    const next = isEsp ? 'local' : 'serial';
    if (next === 'serial' && !s.serial_available) {
      alert('ESP32 não disponível na serial. Verifique o COM em config.json ou conecte o dispositivo. Mantendo PC.');
      await syncOutputState();
      return;
    }
    await fetch(`${API}/output/set?mode=${encodeURIComponent(next)}`, { method:'POST' });
    await syncOutputState();
  }catch(e){
    console.warn('Falha ao alternar modo de saída:', e);
  }
});

syncOutputState();

// Overlay toggle
const overlayToggle = document.getElementById('overlayToggle');
if (overlayToggle){
  overlayToggle.addEventListener('change', async (e) => {
    try{
      const enable = !!e.target.checked;
      await fetch(`${API}/overlay/${enable ? 'enable' : 'disable'}`, { method:'POST' });
    }catch(err){
      console.warn('Falha ao alternar overlay:', err);
    }
  });
}

// Auto iniciar IA na carga da página
(async function autoStartIA(){
  try {
    const s = await fetch(`${API}/state`).then(r=>r.json());
    if (!s.running) {
      await startIA();
      setRunnerState(true);
    }
  } catch (e) {
    console.warn('Falha ao auto-iniciar IA:', e);
  }
})();
