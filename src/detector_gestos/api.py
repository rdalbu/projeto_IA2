import asyncio
import json
import os
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, Response

from .runner import GestureRunner


app = FastAPI(title="IA2 Gesture API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pub/Sub simples para eventos reconhecidos
class EventHub:
    def __init__(self):
        self.queues: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        try:
            self.queues.remove(q)
        except ValueError:
            pass

    def publish_threadsafe(self, loop: asyncio.AbstractEventLoop, event: dict):
        for q in list(self.queues):
            loop.call_soon_threadsafe(q.put_nowait, event)


hub = EventHub()
MAIN_LOOP: asyncio.AbstractEventLoop | None = None


# Runner global
runner: GestureRunner | None = None


def _on_event(evt: dict):
    global MAIN_LOOP
    if MAIN_LOOP:
        hub.publish_threadsafe(MAIN_LOOP, evt)


@app.get("/start")
def start():
    global runner
    if runner and runner.is_running():
        return {"status": "already_running"}
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'config.json'))
    runner = GestureRunner(config_path=config_path, on_event=_on_event)
    runner.start()
    return {"status": "started"}


@app.get("/stop")
def stop():
    global runner
    if runner and runner.is_running():
        runner.stop()
        return {"status": "stopped"}
    return {"status": "not_running"}


@app.get("/state")
def state():
    return {"running": bool(runner and runner.is_running())}


@app.get("/output/state")
def output_state():
    if runner and runner.is_running():
        return runner.get_output_state()
    return {"mode": "local", "serial_available": False}


@app.post("/output/set")
async def output_set(mode: str):
    if not runner or not runner.is_running():
        return {"status": "not_running"}
    ok = runner.set_output_mode(mode)
    return {"status": "ok" if ok else "invalid", **runner.get_output_state()}


@app.get("/kws/state")
def kws_state():
    if runner and runner.is_running():
        return {"enabled": bool(runner.kws_enabled)}
    return {"enabled": False}


@app.post("/kws/enable")
def kws_enable():
    if not runner or not runner.is_running():
        return {"status": "not_running"}
    ok = runner.enable_kws()
    return {"status": "enabled" if ok else "failed"}


@app.post("/kws/disable")
def kws_disable():
    if not runner or not runner.is_running():
        return {"status": "not_running"}
    ok = runner.disable_kws()
    return {"status": "disabled" if ok else "failed"}


@app.post("/test/command")
def test_command(acao: str = "playpause"):
    if not runner or not runner.is_running():
        return {"status": "not_running"}
    acao = (acao or '').lower()
    if acao not in ("playpause","nexttrack","prevtrack"):
        return {"status": "invalid_action"}
    runner.command_queue.put(acao)
    return {"status": "queued", "acao": acao}


@app.get("/frame.jpg")
def frame_jpg():
    if not runner or not runner.is_running():
        return Response(status_code=404)
    data = runner.get_last_frame()
    if not data:
        return Response(status_code=204)
    return Response(content=data, media_type="image/jpeg")


@app.get("/stream")
def stream_mjpeg():
    boundary = "frame"

    async def gen():
        import asyncio as aio
        while runner and runner.is_running():
            data = runner.get_last_frame()
            if data:
                yield (f"--{boundary}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(data)}\r\n\r\n").encode('latin-1') + data + b"\r\n"
            await aio.sleep(0.08)  # ~12 fps
    return StreamingResponse(gen(), media_type=f"multipart/x-mixed-replace; boundary={boundary}")


@app.get("/overlay/state")
def overlay_state():
    if not runner or not runner.is_running():
        return {"enabled": False}
    return {"enabled": bool(runner.preview_overlay)}


@app.post("/overlay/enable")
def overlay_enable():
    if not runner or not runner.is_running():
        return {"status": "not_running"}
    runner.preview_overlay = True
    return {"status": "enabled"}


@app.post("/overlay/disable")
def overlay_disable():
    if not runner or not runner.is_running():
        return {"status": "not_running"}
    runner.preview_overlay = False
    return {"status": "disabled"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    q = hub.subscribe()
    try:
        while True:
            evt = await q.get()
            await ws.send_text(json.dumps(evt, ensure_ascii=False))
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(q)


# Servir o novo front em /front
front_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'front-end'))
if os.path.isdir(front_dir):
    app.mount("/front", StaticFiles(directory=front_dir, html=True), name="front")


@app.on_event("startup")
async def _capture_loop():
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()
