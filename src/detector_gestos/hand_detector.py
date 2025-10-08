import cv2
import mediapipe as mp

class DetectorMaos:
    def __init__(self, modo=False, max_maos=1, deteccao_confianca=0.8, rastreio_confianca=0.8):
        self.modo = modo
        self.max_maos = max_maos
        self.deteccao_confianca = deteccao_confianca
        self.rastreio_confianca = rastreio_confianca

        self.maos_mp = mp.solutions.hands
        self.maos = self.maos_mp.Hands(
            static_image_mode=self.modo,
            max_num_hands=self.max_maos,
            min_detection_confidence=self.deteccao_confianca,
            min_tracking_confidence=self.rastreio_confianca
        )
        self.desenho_mp = mp.solutions.drawing_utils
        self.resultado = None

    def encontrar_maos(self, imagem, desenho=True):
        imagem_rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
        self.resultado = self.maos.process(imagem_rgb)

        if self.resultado.multi_hand_landmarks:
            for pontos in self.resultado.multi_hand_landmarks:
                if desenho:
                    self.desenho_mp.draw_landmarks(imagem, pontos, self.maos_mp.HAND_CONNECTIONS)
        return imagem

    def encontrar_pontos(self, imagem, mao_num=0):
        lista_pontos = []
        if self.resultado.multi_hand_landmarks and len(self.resultado.multi_hand_landmarks) > mao_num:
            mao = self.resultado.multi_hand_landmarks[mao_num]
            altura, largura, _ = imagem.shape

            for id, ponto in enumerate(mao.landmark):
                centro_x, centro_y = int(ponto.x * largura), int(ponto.y * altura)
                lista_pontos.append([id, centro_x, centro_y])
        
        return lista_pontos
