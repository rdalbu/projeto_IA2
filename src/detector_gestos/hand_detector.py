import cv2
import mediapipe as mp
import collections
import math

class DetectorMaos:
    def __init__(self, modo=False, max_maos=2, deteccao_confianca=0.8, rastreio_confianca=0.8, swipe_threshold=70):
        self.modo = modo
        self.max_maos = max_maos
        self.deteccao_confianca = deteccao_confianca
        self.rastreio_confianca = rastreio_confianca
        self.swipe_threshold = swipe_threshold

        self.maos_mp = mp.solutions.hands
        self.maos = self.maos_mp.Hands(
            static_image_mode=self.modo,
            max_num_hands=self.max_maos,
            min_detection_confidence=self.deteccao_confianca,
            min_tracking_confidence=self.rastreio_confianca
        )

        self.desenho_mp = mp.solutions.drawing_utils
        self.historico_dedos = collections.deque(maxlen=10)

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
            
            # Usar o ponto médio entre o dedo indicador e o médio para o deslize
            if len(lista_pontos) > 12:
                ponto_indicador_x = lista_pontos[8][1]
                ponto_medio_x = lista_pontos[12][1]
                ponto_medio_dedos_x = (ponto_indicador_x + ponto_medio_x) // 2
                self.historico_dedos.append(ponto_medio_dedos_x)
        else:
            self.historico_dedos.clear()
            
        return lista_pontos

    def reconhecer_dedos_levantados(self, lista_pontos):
        if len(lista_pontos) < 21:
            return []

        dedos = []
        if lista_pontos[4][1] > lista_pontos[3][1]:
            dedos.append(1)
        else:
            dedos.append(0)
        for tip in [8, 12, 16, 20]:
            if lista_pontos[tip][2] < lista_pontos[tip - 2][2]:
                dedos.append(1)
            else:
                dedos.append(0)
        return dedos

    def reconhecer_gesto_dinamico(self):
        if len(self.historico_dedos) < self.historico_dedos.maxlen:
            return None

        diferenca = self.historico_dedos[-1] - self.historico_dedos[0]
        
        if diferenca > self.swipe_threshold:
            self.historico_dedos.clear()
            return "Deslizar Direita"
        elif diferenca < -self.swipe_threshold:
            self.historico_dedos.clear()
            return "Deslizar Esquerda"
        
        return None

    def reconhecer_gesto(self, lista_pontos):
        if len(lista_pontos) < 21:
            return None

        dedos = self.reconhecer_dedos_levantados(lista_pontos)
        total_dedos = dedos.count(1)

        # Gestos dinâmicos apenas com 2 dedos levantados
        if total_dedos == 2:
            gesto_dinamico = self.reconhecer_gesto_dinamico()
            if gesto_dinamico:
                return gesto_dinamico

        if total_dedos == 5:
            return "Mao Aberta"
        elif total_dedos == 0:
            return "Punho Fechado"

        return None
