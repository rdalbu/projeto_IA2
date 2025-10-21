importargparse
importbase64
importio
importjson
importos
importshutil
importsubprocess
importtempfile
fromtypingimportOptional,Tuple,List

importnumpyasnp
importlibrosa
importsoundfileassf


defhas_ffmpeg()->bool:
    returnshutil.which("ffmpeg")isnotNone


def_ffmpeg_webm_to_wav_bytes(webm_bytes:bytes,sr:int=44100)->Optional[bytes]:
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
            forpin(in_path,out_path):
                try:
                    os.remove(p)
exceptException:
                    pass
exceptException:
        returnNone


defdecode_audio_base64(data_url:str,target_sr:int=44100)->Optional[Tuple[np.ndarray,int]]:
    """Decodifica data URL (WAV ou WebM/Opus) e retorna (y, sr) mono.
    Se for WebM e ffmpeg não estiver disponível, retorna None.
    """
try:
        payload=(data_urlor"")
if","inpayload:
            payload=payload.split(",",1)[1]
raw=base64.b64decode(payload)
exceptException:
        returnNone

iflen(raw)>=4andraw[:4]==b"\x1A\x45\xDF\xA3":
        ifnothas_ffmpeg():
            returnNone
wav_bytes=_ffmpeg_webm_to_wav_bytes(raw,sr=target_sr)
ifnotwav_bytes:
            returnNone
try:
            y,sr=sf.read(io.BytesIO(wav_bytes),dtype='float32',always_2d=False)
exceptException:
            returnNone
else:
        try:
            y,sr=sf.read(io.BytesIO(raw),dtype='float32',always_2d=False)
exceptException:
            try:
                y,sr=librosa.load(io.BytesIO(raw),sr=None,mono=True)
exceptException:
                returnNone

ifisinstance(y,np.ndarray)andy.ndim==2:
        ify.shape[0]==2:
            y=y.mean(axis=0)
else:
            y=y.mean(axis=1)

ifsr!=target_sr:
        y=librosa.resample(y,orig_sr=sr,target_sr=target_sr)
sr=target_sr
returny.astype(np.float32),sr


defcompute_mel_spectrogram(y:np.ndarray,sr:int,
n_fft:int=1024,hop_length:int=441,
n_mels:int=40,fmin:int=0,fmax:int=8000)->np.ndarray:
    S=librosa.feature.melspectrogram(y=y,sr=sr,n_fft=n_fft,hop_length=hop_length,
n_mels=n_mels,fmin=fmin,fmax=fmax,power=2.0)
S_db=librosa.power_to_db(S,ref=np.max)
mn,mx=float(S_db.min()),float(S_db.max())
S_norm=(S_db-mn)/(mx-mn+1e-8)
returnS_norm.astype(np.float32)


defconvert_file(input_path:str,output_path:str,
target_sr:int=44100,
n_fft:int=1024,hop_length:int=441,
n_mels:int=40,fmin:int=0,fmax:int=8000)->None:
    withopen(input_path,'r',encoding='utf-8')asf:
        data=json.load(f)

samples=data.get('samples')or[]
labels=data.get('classes')ordata.get('labels')
ifnotsamples:
        raiseSystemExit("Arquivo sem 'samples'. Nada a converter.")

out_samples:List[dict]=[]
ok=0
total=len(samples)

forsinsamples:
        label=s.get('label')
if'spectrogram'ins:
            spec=s['spectrogram']
out_samples.append({'label':label,'spectrogram':spec})
ok+=1
continue
audio_b64=s.get('audioBase64')
ifnotaudio_b64:
            continue
decoded=decode_audio_base64(audio_b64,target_sr=target_sr)
ifnotdecoded:
            continue
y,sr=decoded
spec=compute_mel_spectrogram(y,sr,n_fft=n_fft,hop_length=hop_length,
n_mels=n_mels,fmin=fmin,fmax=fmax)
out_samples.append({'label':label,'spectrogram':spec.tolist()})
ok+=1

ifnotout_samples:
        raiseSystemExit("Falha ao converter quaisquer amostras. Verifique se há audioBase64 válido e/ou ffmpeg no PATH.")

ifnotlabels:
        labels=sorted(list({s.get('label')forsinout_samplesifs.get('label')isnotNone}))

out={
'classes':labels,
'samples':out_samples,
'config':{
'sampleRate':target_sr,
'n_mels':n_mels,
'n_fft':n_fft,
'hop_length':hop_length,
'fmin':fmin,
'fmax':fmax,
}
}
withopen(output_path,'w',encoding='utf-8')asf:
        json.dump(out,f,ensure_ascii=False)
print(f"Convertido: {ok}/{total} amostras → {output_path}")


defmain():
    parser=argparse.ArgumentParser(description='Converte KWS audioBase64 → spectrogram 2D para treino web.')
parser.add_argument('-i','--input',default='kws-samples.json',help='Arquivo de entrada (com audioBase64 ou spectrogram).')
parser.add_argument('-o','--output',default='kws-samples-spectrogram.json',help='Arquivo de saída (spectrogram).')
parser.add_argument('--sr',type=int,default=44100,help='Sample rate alvo (default: 44100)')
parser.add_argument('--n_fft',type=int,default=1024)
parser.add_argument('--hop',type=int,default=441)
parser.add_argument('--n_mels',type=int,default=40)
parser.add_argument('--fmin',type=int,default=0)
parser.add_argument('--fmax',type=int,default=8000)
args=parser.parse_args()

convert_file(
input_path=args.input,
output_path=args.output,
target_sr=args.sr,
n_fft=args.n_fft,
hop_length=args.hop,
n_mels=args.n_mels,
fmin=args.fmin,
fmax=args.fmax,
)


if__name__=='__main__':
    main()

