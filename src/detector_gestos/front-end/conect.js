const API = "http://127.0.0.1:8000";
let ws = null;

async function startIA() {
  await fetch(`${API}/start`);
  ws = new WebSocket("ws://127.0.0.1:8000/ws");
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("🎯 Gesto detectado:", data.gesture);
    document.getElementById("songTitle").textContent = `🎯 ${data.gesture}`;
  };
}

async function stopIA() {
  await fetch(`${API}/stop`);
  if (ws) ws.close();
}

// Exemplo: integrar com seu switch
document.getElementById("toggleSwitch").addEventListener("click", (e) => {
  const ativo = e.target.classList.toggle("ativo");
  if (ativo) startIA();
  else stopIA();
});
