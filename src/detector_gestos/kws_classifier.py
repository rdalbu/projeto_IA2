
importtensorflowastf
importnumpyasnp
importlibrosa
importjson
importos

classKwsClassifier:
    def__init__(self,model_path,labels_path,sample_rate=16000,duration=1,n_mfcc=13):
        ifnotos.path.exists(model_path):
            raiseFileNotFoundError(f"Modelo KWS não encontrado em: {model_path}")
ifnotos.path.exists(labels_path):
            raiseFileNotFoundError(f"Arquivo de labels KWS não encontrado em: {labels_path}")

self.model=tf.keras.models.load_model(model_path)

withopen(labels_path,'r')asf:
            self.int_to_label=json.load(f)

self.sample_rate=sample_rate
self.duration=duration
self.n_mfcc=n_mfcc
self.expected_length=int(self.sample_rate*self.duration)

defpreprocess(self,audio_data):
        iflen(audio_data)<self.expected_length:
            audio_data=np.pad(audio_data,(0,self.expected_length-len(audio_data)),'constant')
else:
            audio_data=audio_data[:self.expected_length]


mfcc=librosa.feature.mfcc(y=audio_data,sr=self.sample_rate,n_mfcc=self.n_mfcc)


mfcc=np.expand_dims(mfcc,axis=0)
returnmfcc

defpredict(self,audio_data):
        mfcc=self.preprocess(audio_data)


prediction=self.model.predict(mfcc,verbose=0)


predicted_index=np.argmax(prediction)
probability=np.max(prediction)

label=self.int_to_label.get(str(predicted_index),"desconhecido")

returnlabel,probability
