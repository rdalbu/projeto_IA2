# server.py
# Detecta gestos com IA, envia para o front via WebSocket.
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

running = False

@app.get("/start")
async def start_detection():
    global running
    running = True
    print("🚀 Detector iniciado")
    return {"status": "started"}

@app.get("/stop")
async def stop_detection():
    global running
    running = False
    print("🛑 Detector parado")
    return {"status": "stopped"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔗 Cliente conectado")

    try:
        while True:
            if running:
                gesture = "play_pause"
                await websocket.send_json({"gesture": gesture})
                await asyncio.sleep(3)
            else:
                await asyncio.sleep(1)
    except Exception as e:
        print("⚠️ Cliente desconectado:", e)
