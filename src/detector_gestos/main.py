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

command_queue=queue.Queue()
audio_buffer=[]
buffer_lock=threading.Lock()

defload_config(path):
    try:
        withopen(path,'r',encoding='utf-8')asf:
            returnjson.load(f)
exceptFileNotFoundError:
        print(f"Aviso: Arquivo '{os.path.basename(path)}' não encontrado. Usando configurações padrão.")
return{}
exceptjson.JSONDecodeError:
        print(f"Erro: Falha ao decodificar '{os.path.basename(path)}'. Usando configurações padrão.")
return{}

defaudio_callback(indata,frames,time,status):
    ifstatus:
        print(status)
withbuffer_lock:
        audio_buffer.append(indata.copy())

defprocess_audio_thread(kws_classifier,config):
    globalaudio_buffer
min_confidence=config.get("kws_confianca_minima",0.9)
mapeamento_kws=config.get("mapeamento_kws",{})
sample_rate=kws_classifier.sample_rate
duration=kws_classifier.duration
expected_length=int(sample_rate*duration)

print("Thread de processamento de áudio iniciada.")
whileTrue:
        withbuffer_lock:
            iflen(audio_buffer)>0:
                data=np.concatenate(audio_buffer)
audio_buffer.clear()
else:
                data=None

ifdataisnotNoneandlen(data)>=expected_length:
            audio_segment=data[-expected_length:,0]

try:
                label,prob=kws_classifier.predict(audio_segment)
ifprob>=min_confidenceandlabelnotin["neutro","desconhecido"]:
                    acao=mapeamento_kws.get(label)
ifacao:
                        print(f"Palavra-chave: {label} ({prob:.2f}) -> Colocando na fila: '{acao}'")
command_queue.put(acao)
exceptExceptionase:
                print(f"Erro na predição de áudio: {e}")

time.sleep(0.5)


defmain():
    config_path=os.path.join(os.path.dirname(__file__),'..','..','config.json')
config=load_config(config_path)

ser=None
ifconfig.get('usar_serial',False):
        try:
            ser=serial.Serial(
port=config.get('serial_port','COM5'),
baudrate=config.get('serial_baudrate',115200),
timeout=1
)
print(f"Conectado à porta serial {config.get('serial_port','COM5')}.")
exceptserial.SerialExceptionase:
            print(f"ERRO CRÍTICO ao conectar na porta serial: {e}")
print("Verifique se a porta está correta no 'config.json' e se o ESP32 está conectado.")
return

kws_classifier=None
audio_stream=None
usar_kws=bool(config.get("usar_kws"))
ifusar_kws:
        try:
            model_path=config.get("kws_modelo_path")
labels_path=config.get("kws_labels_path")
ifnotmodel_pathornotos.path.exists(model_path):
                raiseFileNotFoundError(f"Modelo KWS não encontrado em '{model_path}'.")
ifnotlabels_pathornotos.path.exists(labels_path):
                raiseFileNotFoundError(f"Arquivo de labels KWS não encontrado em '{labels_path}'.")

kws_classifier=KwsClassifier(
model_path=model_path,
labels_path=labels_path
)

audio_thread=threading.Thread(
target=process_audio_thread,
args=(kws_classifier,config),
daemon=True
)
audio_thread.start()

audio_stream=sd.InputStream(
callback=audio_callback,
samplerate=kws_classifier.sample_rate,
channels=1,
device=config.get("audio_input_device_index")
)
audio_stream.start()
print("Classificador de palavras-chave (KWS) carregado e stream de áudio iniciado.")

exceptExceptionase:
            print("Aviso: KWS desabilitado.")
print("Motivo:",e)
print("- Verifique os caminhos 'kws_modelo_path' e 'kws_labels_path' no config.json")
print("- Ou rode o treino: python treinamento\\train_kws_model.py")
usar_kws=False

cap=None
detector=None
ml_classifier=None
ifconfig.get("usar_modelo_gesto"):
        cap=cv2.VideoCapture(config.get('indice_camera',0))
ifnotcap.isOpened():
            print(f"Erro: Não foi possível abrir a câmera com índice {config.get('indice_camera',0)}.")
ifser:ser.close()
ifaudio_stream:audio_stream.stop()
return

detector=DetectorMaos(
deteccao_confianca=config.get('confianca_deteccao',0.8),
rastreio_confianca=config.get('confianca_rastreamento',0.8)
)
try:
            ml_classifier=KerasGestureClassifier(
model_path=config.get("gesto_modelo_path",""),
labels=config.get("gesto_labels",[]),
)
print("Classificador de gestos (Keras) carregado com sucesso.")
exceptExceptionase:
            print(f"ERRO CRÍTICO ao carregar o modelo de gesto: {e}")
ifser:ser.close()
ifaudio_stream:audio_stream.stop()
return
else:
        print("Aviso: O uso do modelo de gesto está desabilitado em 'config.json'.")


mapeamento_gestos=config.get("mapeamento_gestos",{})
tempo_ultimo_comando=0
ultimo_gesto_detectado=None
contador_frames_gesto=0

print("\n--- Sistema iniciado. Pressione 'ESC' na janela de vídeo para sair. ---")

whileTrue:
        ifcapandml_classifier:
            sucesso,imagem=cap.read()
ifnotsucesso:
                break

imagem=cv2.flip(imagem,1)
imagem=detector.encontrar_maos(imagem)
lista_pontos=detector.encontrar_pontos(imagem)

gesto_atual=None
iflista_pontos:
                try:
                    lbl,prob=ml_classifier.predict(lista_pontos,handedness='Right')
iflblandprob>=config.get("gesto_confianca_minima",0.7):
                        gesto_atual=lbl
exceptExceptionase:
                    print(f"Erro durante a predição de gesto: {e}")

ifgesto_atual==ultimo_gesto_detectadoandgesto_atualisnotNone:
                contador_frames_gesto+=1
else:
                contador_frames_gesto=1
ultimo_gesto_detectado=gesto_atual

gesto_confirmado=None
ifcontador_frames_gesto>=config.get('frames_confirmacao_gesto',5):
                gesto_confirmado=gesto_atual
contador_frames_gesto=0

ifgesto_confirmado:
                acao=mapeamento_gestos.get(gesto_confirmado)
ifacao:
                    command_queue.put(acao)
print(f"Gesto: {gesto_confirmado} -> Colocando na fila: '{acao}'")
else:
            imagem=np.zeros((480,640,3),dtype=np.uint8)
cv2.putText(imagem,"Video desabilitado",(150,240),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2)


try:
            acao_pendente=command_queue.get_nowait()

iftime.time()-tempo_ultimo_comando>config.get('intervalo_entre_comandos_segundos',1.0):
                ifser:
                    try:
                        ser.write(f'{acao_pendente}\n'.encode('utf-8'))
print(f"COMANDO -> Enviando via serial: '{acao_pendente}'")
exceptserial.SerialExceptionase:
                        print(f"Erro ao enviar comando serial: {e}")
else:
                    pyautogui.press(acao_pendente)
print(f"COMANDO -> Ação local (pyautogui): '{acao_pendente}'")

tempo_ultimo_comando=time.time()
cv2.putText(imagem,f"Acao: {acao_pendente}",(50,100),cv2.FONT_HERSHEY_SIMPLEX,1.2,(0,255,0),3)

exceptqueue.Empty:
            pass

cv2.imshow("Controle de Midia por IA",imagem)
ifcv2.waitKey(1)&0xFF==27:
            break

print("\n--- Finalizando o sistema... ---")
ifaudio_stream:
        audio_stream.stop()
audio_stream.close()
print("Stream de áudio fechado.")
ifcap:
        cap.release()
cv2.destroyAllWindows()
ifser:
        ser.close()
print("Porta serial fechada.")

if__name__=='__main__':
    main()
