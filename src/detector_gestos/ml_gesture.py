importmath
importos

try:
    importtensorflowastf
fromtensorflowimportkeras
exceptException:
    tf=None
keras=None


deflandmarks_to_features(landmarks,handedness='Right',include_z=False,mirror_x=True):
    ifnotlandmarksorlen(landmarks)<21:
        returnNone

wrist=landmarks[0]
wx,wy=float(wrist[1]),float(wrist[2])

flip=-1.0if(mirror_xandstr(handedness).lower().startswith('left'))else1.0

pts=[]
for_,x,yinlandmarks:
        rx=(float(x)-wx)*flip
ry=(float(y)-wy)
rz=0.0
pts.append([rx,ry,rz])

max_range=1e-6
forx,y,zinpts:
        max_range=max(max_range,abs(x),abs(y),abs(z))
forpinpts:
        p[0]/=max_range
p[1]/=max_range
p[2]/=max_range

arr=[]
forx,y,zinpts:
        arr.append(x)
arr.append(y)
ifinclude_z:
            arr.append(z)
returnarr


classKerasGestureClassifier:
    def__init__(self,model_path,labels,include_z=False,mirror_x=True):
        iftfisNoneorkerasisNone:
            raiseRuntimeError("TensorFlow ou Keras não está instalado. Instale 'tensorflow' para usar o classificador Keras.")
ifnotos.path.exists(model_path):
            raiseFileNotFoundError(f"Modelo não encontrado em: {model_path}")
ifnotlabelsornotisinstance(labels,list):
            raiseValueError("'labels' precisa ser uma lista com a ordem das classes do modelo.")

self.model=keras.models.load_model(model_path)
self.labels=labels
self.include_z=include_z
self.mirror_x=mirror_x

defpredict(self,landmarks,handedness='Right'):
        feat=landmarks_to_features(landmarks,handedness,self.include_z,self.mirror_x)
ifnotfeat:
            returnNone,0.0
x=tf.convert_to_tensor([feat],dtype=tf.float32)
probs=self.model(x,training=False).numpy()[0]
idx=int(max(range(len(probs)),key=lambdai:probs[i]))
returnself.labels[idx],float(probs[idx])

