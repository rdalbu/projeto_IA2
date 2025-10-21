importcv2
importmediapipeasmp

classDetectorMaos:
    def__init__(self,modo=False,max_maos=1,deteccao_confianca=0.8,rastreio_confianca=0.8):
        self.modo=modo
self.max_maos=max_maos
self.deteccao_confianca=deteccao_confianca
self.rastreio_confianca=rastreio_confianca

self.maos_mp=mp.solutions.hands
self.maos=self.maos_mp.Hands(
static_image_mode=self.modo,
max_num_hands=self.max_maos,
min_detection_confidence=self.deteccao_confianca,
min_tracking_confidence=self.rastreio_confianca
)
self.desenho_mp=mp.solutions.drawing_utils
self.resultado=None
self._ultima_mao=[]

defencontrar_maos(self,imagem,desenho=True):
        imagem_rgb=cv2.cvtColor(imagem,cv2.COLOR_BGR2RGB)
self.resultado=self.maos.process(imagem_rgb)

self._ultima_mao=[]
try:
            ifself.resultadoandgetattr(self.resultado,'multi_handedness',None):
                forhinself.resultado.multi_handedness:

                    label=None
try:
                        label=h.classification[0].label
exceptException:
                        label=None
self._ultima_mao.append(labelor'Right')
exceptException:
            self._ultima_mao=[]

ifself.resultado.multi_hand_landmarks:
            forpontosinself.resultado.multi_hand_landmarks:
                ifdesenho:
                    self.desenho_mp.draw_landmarks(imagem,pontos,self.maos_mp.HAND_CONNECTIONS)
returnimagem

defencontrar_pontos(self,imagem,mao_num=0):
        lista_pontos=[]
ifself.resultado.multi_hand_landmarksandlen(self.resultado.multi_hand_landmarks)>mao_num:
            mao=self.resultado.multi_hand_landmarks[mao_num]
altura,largura,_=imagem.shape

forid,pontoinenumerate(mao.landmark):
                centro_x,centro_y=int(ponto.x*largura),int(ponto.y*altura)
lista_pontos.append([id,centro_x,centro_y])

returnlista_pontos

defget_handedness(self,mao_num=0):
        ifself._ultima_maoandlen(self._ultima_mao)>mao_num:
            returnself._ultima_mao[mao_num]
return'Right'
