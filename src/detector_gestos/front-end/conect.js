const API = "http://127.0.0.1:8000";
let ws = null;

async function startIA() {
  console.log("🚀 Iniciando IA...");
  await fetch(`${API}/start`);
  ws = new WebSocket("ws://127.0.0.1:8000/ws");

  ws.onopen = () => console.log("✅ Conectado ao backend via WebSocket");

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("🎯 Gesto detectado:", data.gesture);
    document.getElementById("songTitle").textContent = `🎯 ${data.gesture}`;
  };

  ws.onclose = () => console.log("⚠️ WebSocket fechado");
  ws.onerror = (err) => console.error("❌ Erro no WebSocket:", err);
}

async function stopIA() {
  console.log("🛑 Parando IA...");
  await fetch(`${API}/stop`);
  if (ws) ws.close();
}

document.getElementById("toggleSwitch").addEventListener("click", (e) => {
  const ativo = e.target.classList.toggle("ativo");
  if (ativo) startIA();
  else stopIA();
});
