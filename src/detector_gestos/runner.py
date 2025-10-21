importcv2
importpyautogui
importtime
importjson
importos
importserial
importthreading
importqueue
importnumpyasnp
importsounddeviceassd

from.hand_detectorimportDetectorMaos
from.ml_gestureimportKerasGestureClassifier
from.kws_classifierimportKwsClassifier


try:
    importplatform
importctypes
_IS_WINDOWS=platform.system().lower().startswith('win')
exceptException:
    _IS_WINDOWS=False

VK_MEDIA={
'playpause':0xB3,
'nexttrack':0xB0,
'prevtrack':0xB1,
}

defsend_media_key_local(action:str):
    if_IS_WINDOWSandactioninVK_MEDIA:
        try:
            vk=VK_MEDIA[action]
ctypes.windll.user32.keybd_event(vk,0,0,0)
ctypes.windll.user32.keybd_event(vk,0,2,0)
returnTrue
exceptException:
            returnFalse

try:
        pyautogui.press(action)
returnTrue
exceptException:
        returnFalse


classGestureRunner:
    def__init__(self,config_path,on_event=None):
        self.config_path=config_path
self.on_event=on_eventor(lambdaevt:None)

self._thread=None
self._stop=threading.Event()
self._audio_thread=None

self.command_queue=queue.Queue()
self.audio_buffer=[]
self.buffer_lock=threading.Lock()

self.ser=None
self.audio_stream=None
self.cap=None
self.detector=None
self.ml_classifier=None
self.kws_classifier=None
self.kws_enabled=False
self.output_mode="auto"

self._frame_lock=threading.Lock()
self._last_jpeg=None
self.preview_overlay=True
self._last_preview_ts=0.0
self._preview_interval=1.0/15.0
self.jpeg_quality=70

self.config={}

def_load_config(self):
        try:
            withopen(self.config_path,'r',encoding='utf-8')asf:
                self.config=json.load(f)
exceptException:
            self.config={}

def_audio_callback(self,indata,frames,time_info,status):
        ifstatus:
            print(status)
withself.buffer_lock:
            self.audio_buffer.append(indata.copy())

def_process_audio_thread(self):
        cfg=self.config
min_conf=cfg.get("kws_confianca_minima",0.9)
mapeamento=cfg.get("mapeamento_kws",{})
sample_rate=self.kws_classifier.sample_rate
duration=self.kws_classifier.duration
expected_length=int(sample_rate*duration)

whilenotself._stop.is_set():
            ifnotself.kws_enabledorself.kws_classifierisNone:
                time.sleep(0.2)
continue
withself.buffer_lock:
                data=np.concatenate(self.audio_buffer)ifself.audio_bufferelseNone
self.audio_buffer.clear()

ifdataisnotNoneandlen(data)>=expected_length:
                audio_segment=data[-expected_length:,0]
try:
                    label,prob=self.kws_classifier.predict(audio_segment)
ifprob>=min_confandlabelnotin["neutro","desconhecido"]:
                        acao=mapeamento.get(label)
ifacao:
                            self.on_event({
"type":"kws",
"label":label,
"prob":float(prob),
"action":acao,
"ts":time.time(),
})
self.command_queue.put(acao)
exceptExceptionase:
                    print(f"Erro na predição de áudio: {e}")

time.sleep(0.3)

defstart(self):
        ifself._threadandself._thread.is_alive():
            returnFalse
self._stop.clear()
self._thread=threading.Thread(target=self._run,daemon=True)
self._thread.start()
returnTrue

defstop(self):
        self._stop.set()

ifself.audio_stream:
            try:
                self.audio_stream.stop()
self.audio_stream.close()
exceptException:
                pass
self.audio_stream=None

ifself.cap:
            try:
                self.cap.release()
exceptException:
                pass
self.cap=None

ifself.ser:
            try:
                self.ser.close()
exceptException:
                pass
self.ser=None

defis_running(self):
        returnbool(self._threadandself._thread.is_alive())

defset_output_mode(self,mode:str):
        mode=(modeor"").lower()
ifmodein("auto","serial","local"):
            self.output_mode=mode
returnTrue
returnFalse

defget_output_state(self):
        return{
"mode":self.output_mode,
"serial_available":bool(self.ser),
}

defget_last_frame(self):
        withself._frame_lock:
            returnself._last_jpeg

defenable_kws(self)->bool:
        ifself.kws_enabled:
            returnTrue
cfg=self.config
try:
            mp=cfg.get("kws_modelo_path")
lp=cfg.get("kws_labels_path")
ifnotmpornotos.path.exists(mp):
                raiseFileNotFoundError(f"Modelo KWS não encontrado: {mp}")
ifnotlpornotos.path.exists(lp):
                raiseFileNotFoundError(f"Labels KWS não encontrado: {lp}")

ifself.kws_classifierisNone:
                self.kws_classifier=KwsClassifier(mp,lp)

ifnotself._audio_threadornotself._audio_thread.is_alive():
                self._audio_thread=threading.Thread(target=self._process_audio_thread,daemon=True)
self._audio_thread.start()

ifnotself.audio_stream:
                self.audio_stream=sd.InputStream(
callback=self._audio_callback,
samplerate=self.kws_classifier.sample_rate,
channels=1,
device=cfg.get("audio_input_device_index")
)
self.audio_stream.start()
self.kws_enabled=True
returnTrue
exceptExceptionase:
            print("Falha ao habilitar KWS:",e)
self.kws_enabled=False
returnFalse

defdisable_kws(self)->bool:
        self.kws_enabled=False
try:
            ifself.audio_stream:
                try:
                    self.audio_stream.stop()
self.audio_stream.close()
exceptException:
                    pass
self.audio_stream=None

returnTrue
finally:
            returnTrue

def_run(self):
        self._load_config()
cfg=self.config

try:
            max_fps=float(cfg.get('preview_max_fps',15))
self._preview_interval=1.0/max(1.0,max_fps)
exceptException:
            self._preview_interval=1.0/15.0
try:
            self.jpeg_quality=int(cfg.get('jpeg_quality',70))
exceptException:
            self.jpeg_quality=70


self.ser=None
ifcfg.get('usar_serial',False):
            try:
                self.ser=serial.Serial(
port=cfg.get('serial_port','COM5'),
baudrate=cfg.get('serial_baudrate',115200),
timeout=1
)
print(f"Conectado à porta serial {cfg.get('serial_port','COM5')}.")
exceptserial.SerialExceptionase:
                print(f"Aviso: falha ao abrir serial: {e}. Usando pyautogui.")
self.ser=None

self.output_mode="serial"ifself.serelse"local"


self.kws_classifier=None
self.audio_stream=None
ifcfg.get("usar_kws"):
            try:
                mp=cfg.get("kws_modelo_path")
lp=cfg.get("kws_labels_path")
ifnotmpornotos.path.exists(mp):
                    raiseFileNotFoundError(f"Modelo KWS não encontrado: {mp}")
ifnotlpornotos.path.exists(lp):
                    raiseFileNotFoundError(f"Labels KWS não encontrado: {lp}")
self.kws_classifier=KwsClassifier(mp,lp)
self._audio_thread=threading.Thread(target=self._process_audio_thread,daemon=True)
self._audio_thread.start()
self.audio_stream=sd.InputStream(
callback=self._audio_callback,
samplerate=self.kws_classifier.sample_rate,
channels=1,
device=cfg.get("audio_input_device_index")
)
self.audio_stream.start()
self.kws_enabled=True
print("KWS iniciado.")
exceptExceptionase:
                print("Aviso: KWS desabilitado:",e)
self.kws_classifier=None
self.kws_enabled=False


self.cap=None
self.detector=None
self.ml_classifier=None
ifcfg.get("usar_modelo_gesto"):
            cam_index=cfg.get('indice_camera',0)
self.cap=cv2.VideoCapture(cam_index)
ifnotself.cap.isOpened():
                print(f"Aviso: falha ao abrir camera idx {cfg.get('indice_camera',0)}. Gestos desabilitados.")
self.cap=None
else:

                try:
                    w=int(cfg.get('camera_width',640))
h=int(cfg.get('camera_height',480))
self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,w)
self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,h)
target_fps=float(cfg.get('camera_fps',30))
self.cap.set(cv2.CAP_PROP_FPS,target_fps)
exceptException:
                    pass
self.detector=DetectorMaos(
deteccao_confianca=cfg.get('confianca_deteccao',0.8),
rastreio_confianca=cfg.get('confianca_rastreamento',0.8)
)
try:
                    self.ml_classifier=KerasGestureClassifier(
model_path=cfg.get("gesto_modelo_path",""),
labels=cfg.get("gesto_labels",[]),
)
print("Classificador de gestos iniciado.")
exceptExceptionase:
                    print("Aviso: Gestos desabilitados:",e)
self.ml_classifier=None

mapeamento_gestos=cfg.get("mapeamento_gestos",{})
tempo_ultimo=0.0
ultimo_lbl=None
frames_ok=0
min_prob=cfg.get("gesto_confianca_minima",0.7)
cooldown=float(cfg.get('intervalo_entre_comandos_segundos',1.0))
next_allowed_ts=0.0

whilenotself._stop.is_set():
            imagem=None

ifself.cap:
                ok,imagem=self.cap.read()
ifnotok:
                    break
imagem=cv2.flip(imagem,1)
ifself.detector:
                    imagem=self.detector.encontrar_maos(imagem,desenho=self.preview_overlay)
pts=self.detector.encontrar_pontos(imagem)
else:
                    pts=[]

try:
                    now=time.time()
if(now-self._last_preview_ts)>=self._preview_interval:
                        params=[int(cv2.IMWRITE_JPEG_QUALITY),int(self.jpeg_quality)]
ok_jpg,buf=cv2.imencode('.jpg',imagem,params)
ifok_jpg:
                            withself._frame_lock:
                                self._last_jpeg=buf.tobytes()
self._last_preview_ts=now
exceptException:
                    pass

lbl=None
prob=0.0
has_pts=bool(pts)
ifhas_ptsandself.ml_classifierandself.detector:
                    try:
                        handed=self.detector.get_handedness(0)
lbl,prob=self.ml_classifier.predict(pts,handedness=handedor'Right')
exceptExceptionase:
                        print("Erro predição gesto:",e)
lbl,prob=None,0.0

atual=lblif(lblandprob>=min_prob)elseNone
ifatual==ultimo_lblandatualisnotNone:
                    frames_ok+=1
else:
                    frames_ok=1
ultimo_lbl=atual

ifframes_ok>=cfg.get('frames_confirmacao_gesto',5):
                    frames_ok=0
ifatual:
                        acao=mapeamento_gestos.get(atual)
ifacao:
                            now=time.time()
ifnow>=next_allowed_ts:

                                self.command_queue.put({
'acao':acao,
'label':atual,
'prob':float(prob),
'ts':now,
})
next_allowed_ts=now+cooldown


try:
                item=self.command_queue.get_nowait()

ifisinstance(item,dict):
                    acao=item.get('acao')
meta=item
else:
                    acao=item
meta={'acao':acao,'label':None,'prob':0.0,'ts':time.time()}

iftime.time()-tempo_ultimo>cooldown:
                    chosen=self.output_mode
ifchosen=="auto":
                        chosen="serial"ifself.serelse"local"
ifchosen=="serial"andself.ser:
                        try:
                            self.ser.write(f"{acao}\n".encode('utf-8'))
print(f"SERIAL -> {acao}")
exceptserial.SerialExceptionase:
                            print("Erro serial:",e)
else:
                        ok_local=send_media_key_local(acao)
print(f"LOCAL -> {acao}{''ifok_localelse' (fallback falhou)'}")
tempo_ultimo=time.time()

self.on_event({
'type':'gesture',
'label':meta.get('label'),
'prob':meta.get('prob',0.0),
'action':acao,
'ts':tempo_ultimo,
})
exceptqueue.Empty:
                pass

time.sleep(0.01)
