importos
importio
importbase64
importnumpyasnp
importjson
importshutil
fromsklearn.model_selectionimporttrain_test_split
importkeras
fromkeras.modelsimportSequential
fromkeras.layersimportConv2D,MaxPooling2D,Flatten,Dense,Dropout,Reshape,GlobalAveragePooling2D
fromkeras.utilsimportto_categorical
fromkeras.callbacksimportEarlyStopping,ReduceLROnPlateau
importlibrosa
importsoundfileassf
importsubprocess
importtempfile

INPUT_JSON_PATH="kws-samples.json"
OUTPUT_MODEL_DIR="models/kws"
OUTPUT_MODEL_NAME="kws_model.h5"
OUTPUT_LABELS_NAME="kws_labels.json"

TEST_SIZE=0.2
VALIDATION_SIZE=0.2
BATCH_SIZE=32
EPOCHS=50

_FFMPEG_AVAILABLE=shutil.which('ffmpeg')isnotNone
_FFMPEG_WARNED=False

def_ffmpeg_webm_to_wav_bytes(webm_bytes:bytes,sr:int=16000)->bytes|None:
    """Converte bytes WebM/Opus para WAV PCM mono em sr especificada via ffmpeg.
    Retorna bytes do WAV ou None se falhar/ffmpeg ausente.
    """
try:
        withtempfile.NamedTemporaryFile(suffix=".webm",delete=False)asf_in:
            in_path=f_in.name
f_in.write(webm_bytes)
withtempfile.NamedTemporaryFile(suffix=".wav",delete=False)asf_out:
            out_path=f_out.name
try:
            cmd=[
"ffmpeg","-y","-loglevel","error",
"-i",in_path,
"-ac","1",
"-ar",str(sr),
out_path,
]
subprocess.run(cmd,check=True)
withopen(out_path,"rb")asf:
                returnf.read()
finally:
            try:
                os.remove(in_path)
exceptException:
                pass
try:
                os.remove(out_path)
exceptException:
                pass
exceptFileNotFoundError:
        returnNone
exceptExceptionase:
        print("Aviso: falha na convers\u00e3o WebM via ffmpeg:",e)
returnNone


def_decode_wav_base64_to_mfcc(audio_b64:str,sr:int=16000,duration:float=1.0,n_mfcc:int=13):
    try:
        audio_b64=(audio_b64or"").strip()
if","inaudio_b64:
            audio_b64=audio_b64.split(",",1)[1]
wav_or_webm_bytes=base64.b64decode(audio_b64)
iflen(wav_or_webm_bytes)>=4andwav_or_webm_bytes[:4]==b"\x1A\x45\xDF\xA3":
            wav_bytes=_ffmpeg_webm_to_wav_bytes(wav_or_webm_bytes,sr=sr)
ifnotwav_bytes:
                returnNone
else:
            wav_bytes=wav_or_webm_bytes

try:
            y,sr0=sf.read(io.BytesIO(wav_bytes),dtype='float32',always_2d=False)
ifyisNone:
                returnNone
ifisinstance(y,np.ndarray)andy.ndim==2:
                ify.shape[0]==2:
                    y=y.mean(axis=0)
else:
                    y=y.mean(axis=1)
exceptException:
            y,sr0=librosa.load(io.BytesIO(wav_bytes),sr=None,mono=True)

ifsr0!=sr:
            y=librosa.resample(y,orig_sr=sr0,target_sr=sr)

expected_len=int(sr*duration)
iflen(y)<expected_len:
            y=np.pad(y,(0,expected_len-len(y)),mode='constant')
else:
            y=y[:expected_len]
mfcc=librosa.feature.mfcc(y=y,sr=sr,n_mfcc=n_mfcc)
returnmfcc
exceptException:
        returnNone


defload_data_from_json(json_path):
    print(f"Carregando dataset de '{json_path}'...")
withopen(json_path,'r',encoding='utf-8')asf:
        data=json.load(f)

labels=data.get('classes')ordata.get('labels')
samples=data.get('samples')or[]
ifnotlabelsornotisinstance(samples,list):
        raiseValueError("JSON de dataset inválido: esperado chaves 'classes' e 'samples'.")


uses_spectrogram=(len(samples)>0)and('spectrogram'insamples[0])
uses_audio_b64=(len(samples)>0)and('audioBase64'insamples[0])


is_webm=False
ifuses_audio_b64andlen(samples)>0:
        try:
            probe_b64=(samples[0].get('audioBase64')or'').split(',',1)[-1]
probe_bytes=base64.b64decode(probe_b64)
is_webm=len(probe_bytes)>=4andprobe_bytes[:4]==b"\x1A\x45\xDF\xA3"
exceptException:
            is_webm=False


ifuses_spectrogram:
        print("Formato detectado: samples[].spectrogram (pronto para treino)")
elifuses_audio_b64:
        ifis_webm:
            print(f"Formato detectado: samples[].audioBase64 = WebM/Opus (MediaRecorder) | ffmpeg disponível: {'sim'if_FFMPEG_AVAILABLEelse'não'}")
else:
            print("Formato detectado: samples[].audioBase64 = WAV/PCM")
else:
        print("Formato detectado: desconhecido")


ifuses_audio_b64andis_webmandnot_FFMPEG_AVAILABLE:
        raiseSystemExit(
"Dataset usa audioBase64 em WebM/Opus e o ffmpeg não está no PATH.\n"
"Opções: instale o ffmpeg e rode novamente, ou reexporte pelo navegador "
"em formato de espectrogramas (kws-samples.json com samples[].spectrogram)."
)

X_list=[]
y_labels=[]

decoded=0
total=len(samples)

ifuses_spectrogram:

        forsinsamples:
            spec=np.array(s['spectrogram'],dtype=np.float32)
X_list.append(spec)
y_labels.append(s['label'])
decoded+=1

ifX_listandgetattr(X_list[0],'ndim',0)==2:
            target_w=int(X_list[0].shape[1])
X_list=[x[:,:target_w]ifx.shape[1]>=target_welsenp.pad(x,((0,0),(0,target_w-x.shape[1])),mode='constant')forxinX_list]

ifX_listandgetattr(X_list[0],'ndim',0)==2:
            target_w=int(X_list[0].shape[1])
X_list=[x[:,:target_w]ifx.shape[1]>=target_welsenp.pad(x,((0,0),(0,target_w-x.shape[1])),mode='constant')forxinX_list]
elifuses_audio_b64:

        foridx,sinenumerate(samples):
            mfcc=_decode_wav_base64_to_mfcc(s.get('audioBase64',''))
ifmfccisNone:
                continue
X_list.append(mfcc.astype(np.float32))
y_labels.append(s['label'])
decoded+=1
ifnotX_list:
            raiseValueError("Falha ao decodificar qualquer amostra de áudio base64.")



target_w=X_list[0].shape[1]
X_list=[x[:,:target_w]ifx.shape[1]>=target_welsenp.pad(x,((0,0),(0,target_w-x.shape[1])),mode='constant')forxinX_list]
else:
        raiseValueError("Formato de samples não reconhecido: esperava 'spectrogram' ou 'audioBase64'.")

X=np.stack(X_list,axis=0).astype(np.float32)
print(f"Shape X: {X.shape}")
print(f"Amostras decodificadas: {decoded}/{total}")

label_to_int={label:ifori,labelinenumerate(labels)}
y=np.array([label_to_int[lbl]forlbliny_labels],dtype=np.int64)


int_to_label={i:labelfori,labelinenumerate(labels)}
ifnotos.path.exists(OUTPUT_MODEL_DIR):
        os.makedirs(OUTPUT_MODEL_DIR)
labels_path=os.path.join(OUTPUT_MODEL_DIR,OUTPUT_LABELS_NAME)
withopen(labels_path,'w',encoding='utf-8')asf:
        json.dump(int_to_label,f,ensure_ascii=False)
print(f"Labels salvos em {labels_path}")

returnX,y,labels

defbuild_model(input_shape,num_classes):

    iflen(input_shape)!=2:
        raiseValueError(f"input_shape inválido para KWS: {input_shape}. Esperado (H, W).")
h,w=int(input_shape[0]),int(input_shape[1])
model=Sequential([
keras.layers.Input(shape=(h,w)),
Reshape((h,w,1)),

Conv2D(8,(2,2),activation='relu'),
MaxPooling2D((2,2),strides=(2,2)),

Conv2D(16,(2,2),activation='relu'),
MaxPooling2D((2,2),strides=(2,2)),

GlobalAveragePooling2D(),
Dropout(0.25),
Dense(64,activation='relu'),
Dropout(0.5),
Dense(num_classes,activation='softmax')
])

model.compile(optimizer='adam',loss='categorical_crossentropy',metrics=['accuracy'])
returnmodel

defmain():
    print("--- Treinamento do Modelo de Key-Word Spotting (KWS) ---")

ifnotos.path.exists(INPUT_JSON_PATH):
        print(f"ERRO: Arquivo de dados '{INPUT_JSON_PATH}' não encontrado.")
print("Por favor, colete as amostras de voz na interface web e exporte o arquivo 'kws-samples.json' para a raiz do projeto.")
return

X,y,labels=load_data_from_json(INPUT_JSON_PATH)
iflen(X)==0:
        print("Nenhum dado encontrado no arquivo JSON.")
return

num_classes=len(labels)
y_cat=to_categorical(y,num_classes=num_classes)

print("\n2. Dividindo os dados...")
X_train,X_test,y_train,y_test=train_test_split(X,y_cat,test_size=TEST_SIZE,stratify=y,random_state=42)
X_train,X_val,y_train,y_val=train_test_split(X_train,y_train,test_size=VALIDATION_SIZE,stratify=y_train,random_state=42)

print(f"  - Dados de treino: {X_train.shape[0]} amostras")
print(f"  - Dados de validação: {X_val.shape[0]} amostras")
print(f"  - Dados de teste: {X_test.shape[0]} amostras")

print("\n3. Construindo o modelo de rede neural...")
input_shape=X_train.shape[1:]
model=build_model(input_shape,num_classes)
model.summary()

print("\n4. Iniciando o treinamento...")
callbacks=[
EarlyStopping(monitor='val_loss',patience=10,restore_best_weights=True),
ReduceLROnPlateau(monitor='val_loss',factor=0.2,patience=5,min_lr=0.0001)
]

history=model.fit(
X_train,y_train,
epochs=EPOCHS,
batch_size=BATCH_SIZE,
validation_data=(X_val,y_val),
callbacks=callbacks
)

print("\n5. Avaliando o modelo com os dados de teste...")
test_loss,test_acc=model.evaluate(X_test,y_test,verbose=0)
print(f"  - Acurácia no teste: {test_acc:.2f}")
print(f"  - Perda no teste: {test_loss:.4f}")

print("\n6. Salvando o modelo treinado (.h5)...")
model_path=os.path.join(OUTPUT_MODEL_DIR,OUTPUT_MODEL_NAME)
model.save(model_path)
print(f"Modelo salvo em: {model_path}")

print("\n7. Convertendo modelo para formato TensorFlow.js...")
output_web_dir=os.path.join(os.path.dirname(OUTPUT_MODEL_DIR),'kws_web')
try:
        ifnotos.path.exists(output_web_dir):
            os.makedirs(output_web_dir)

labels_path=os.path.join(OUTPUT_MODEL_DIR,OUTPUT_LABELS_NAME)
shutil.copy(labels_path,output_web_dir)


try:
            importtensorflowjsastfjs
fromtensorflowjs.convertersimportsave_keras_model
print("Convertendo via API do tensorflowjs…")
save_keras_model(model,output_web_dir)
print(f"Modelo convertido com sucesso para: {output_web_dir}")
exceptExceptionasapi_err:
            print(f"Falha na API tensorflowjs ({api_err}). Tentando via CLI…")
command=f'tensorflowjs_converter --input_format=keras {model_path} {output_web_dir}'
print(f"Executando: {command}")
result=os.system(command)
ifresult==0:
                print(f"Modelo convertido com sucesso para: {output_web_dir}")
else:
                raiseException(f"O comando tensorflowjs_converter falhou com código de saída {result}.")
exceptExceptionase:
        print(f"ERRO durante a conversão para TensorFlow.js: {e}")
print("  - Instale o pacote: pip install tensorflowjs")
print("  - Ou adicione o executável tensorflowjs_converter ao PATH.")

print("\n--- Treinamento concluído! ---")

if__name__=='__main__':
    main()
