importasyncio
importjson
importos
fromtypingimportList

fromfastapiimportFastAPI,WebSocket,WebSocketDisconnect
fromfastapi.middleware.corsimportCORSMiddleware
fromfastapi.staticfilesimportStaticFiles
fromfastapi.responsesimportStreamingResponse,Response

from.runnerimportGestureRunner


app=FastAPI(title="IA2 Gesture API")

app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)



classEventHub:
    def__init__(self):
        self.queues:List[asyncio.Queue]=[]

defsubscribe(self)->asyncio.Queue:
        q:asyncio.Queue=asyncio.Queue()
self.queues.append(q)
returnq

defunsubscribe(self,q:asyncio.Queue):
        try:
            self.queues.remove(q)
exceptValueError:
            pass

defpublish_threadsafe(self,loop:asyncio.AbstractEventLoop,event:dict):
        forqinlist(self.queues):
            loop.call_soon_threadsafe(q.put_nowait,event)


hub=EventHub()
MAIN_LOOP:asyncio.AbstractEventLoop|None=None



runner:GestureRunner|None=None


def_on_event(evt:dict):
    globalMAIN_LOOP
ifMAIN_LOOP:
        hub.publish_threadsafe(MAIN_LOOP,evt)


@app.get("/start")
defstart():
    globalrunner
ifrunnerandrunner.is_running():
        return{"status":"already_running"}
config_path=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','config.json'))
runner=GestureRunner(config_path=config_path,on_event=_on_event)
runner.start()
return{"status":"started"}


@app.get("/stop")
defstop():
    globalrunner
ifrunnerandrunner.is_running():
        runner.stop()
return{"status":"stopped"}
return{"status":"not_running"}


@app.get("/state")
defstate():
    return{"running":bool(runnerandrunner.is_running())}


@app.get("/output/state")
defoutput_state():
    ifrunnerandrunner.is_running():
        returnrunner.get_output_state()
return{"mode":"local","serial_available":False}


@app.post("/output/set")
asyncdefoutput_set(mode:str):
    ifnotrunnerornotrunner.is_running():
        return{"status":"not_running"}
ok=runner.set_output_mode(mode)
return{"status":"ok"ifokelse"invalid",**runner.get_output_state()}


@app.get("/kws/state")
defkws_state():
    ifrunnerandrunner.is_running():
        return{"enabled":bool(runner.kws_enabled)}
return{"enabled":False}


@app.post("/kws/enable")
defkws_enable():
    ifnotrunnerornotrunner.is_running():
        return{"status":"not_running"}
ok=runner.enable_kws()
return{"status":"enabled"ifokelse"failed"}


@app.post("/kws/disable")
defkws_disable():
    ifnotrunnerornotrunner.is_running():
        return{"status":"not_running"}
ok=runner.disable_kws()
return{"status":"disabled"ifokelse"failed"}


@app.post("/test/command")
deftest_command(acao:str="playpause"):
    ifnotrunnerornotrunner.is_running():
        return{"status":"not_running"}
acao=(acaoor'').lower()
ifacaonotin("playpause","nexttrack","prevtrack"):
        return{"status":"invalid_action"}
runner.command_queue.put(acao)
return{"status":"queued","acao":acao}


@app.get("/frame.jpg")
defframe_jpg():
    ifnotrunnerornotrunner.is_running():
        returnResponse(status_code=404)
data=runner.get_last_frame()
ifnotdata:
        returnResponse(status_code=204)
returnResponse(content=data,media_type="image/jpeg")


@app.get("/stream")
defstream_mjpeg():
    boundary="frame"

asyncdefgen():
        importasyncioasaio
whilerunnerandrunner.is_running():
            data=runner.get_last_frame()
ifdata:
                yield(f"--{boundary}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(data)}\r\n\r\n").encode('latin-1')+data+b"\r\n"
awaitaio.sleep(0.08)
returnStreamingResponse(gen(),media_type=f"multipart/x-mixed-replace; boundary={boundary}")


@app.get("/overlay/state")
defoverlay_state():
    ifnotrunnerornotrunner.is_running():
        return{"enabled":False}
return{"enabled":bool(runner.preview_overlay)}


@app.post("/overlay/enable")
defoverlay_enable():
    ifnotrunnerornotrunner.is_running():
        return{"status":"not_running"}
runner.preview_overlay=True
return{"status":"enabled"}


@app.post("/overlay/disable")
defoverlay_disable():
    ifnotrunnerornotrunner.is_running():
        return{"status":"not_running"}
runner.preview_overlay=False
return{"status":"disabled"}


@app.websocket("/ws")
asyncdefws_endpoint(ws:WebSocket):
    awaitws.accept()
q=hub.subscribe()
try:
        whileTrue:
            evt=awaitq.get()
awaitws.send_text(json.dumps(evt,ensure_ascii=False))
exceptWebSocketDisconnect:
        pass
finally:
        hub.unsubscribe(q)



front_dir=os.path.abspath(os.path.join(os.path.dirname(__file__),'front-end'))
ifos.path.isdir(front_dir):
    app.mount("/front",StaticFiles(directory=front_dir,html=True),name="front")


@app.on_event("startup")
asyncdef_capture_loop():
    globalMAIN_LOOP
MAIN_LOOP=asyncio.get_running_loop()
