import cv2
import mediapipe as mp
import pyautogui
import time
import collections
import json
import os


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
        self.historico_punho = collections.deque(maxlen=10)

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
            
            self.historico_punho.append(lista_pontos[0][1])
        else:
            self.historico_punho.clear()
            
        return lista_pontos

    def reconhecer_gesto(self, lista_pontos):
        if len(lista_pontos) < 21:
            return None

        gesto_estatico = None
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
        total_dedos = dedos.count(1)

        if total_dedos == 5:
            gesto_estatico = "Mão Aberta"
        elif total_dedos == 0:
            gesto_estatico = "Punho Fechado"

        gesto_dinamico = None
        if len(self.historico_punho) == self.historico_punho.maxlen:
            diferenca = self.historico_punho[-1] - self.historico_punho[0]
            
            if diferenca > self.swipe_threshold:
                gesto_dinamico = "Deslizar Direita"
                self.historico_punho.clear()
            elif diferenca < -self.swipe_threshold:
                gesto_dinamico = "Deslizar Esquerda"
                self.historico_punho.clear()

        return gesto_dinamico if gesto_dinamico else gesto_estatico

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("Erro: Arquivo config.json não encontrado! Usando valores padrão.")
        return None
    except json.JSONDecodeError:
        print("Erro: Falha ao decodificar o arquivo config.json! Verifique a formatação.")
        return None

def main():
    config = load_config()
    if config is None:
        # Valores padrão em português
        config = {
            "indice_camera": 0,
            "confianca_deteccao": 0.8,
            "confianca_rastreamento": 0.8,
            "sensibilidade_deslize_pixels": 70,
            "frames_confirmacao_gesto": 5,
            "intervalo_entre_comandos_segundos": 1.0
        }

    cap = cv2.VideoCapture(config['indice_camera'])
    detector = DetectorMaos(
        deteccao_confianca=config['confianca_deteccao'],
        rastreio_confianca=config['confianca_rastreamento'],
        swipe_threshold=config['sensibilidade_deslize_pixels']
    )

    tempo_ultimo_comando = 0
    intervalo_comandos = config['intervalo_entre_comandos_segundos']
    ultimo_gesto_detectado = None
    contador_frames_gesto = 0
    FRAMES_PARA_CONFIRMAR = config['frames_confirmacao_gesto']

    while True:
        _, imagem = cap.read()
        if not _:
            print("Erro: Não foi possível ler a imagem da câmera. Verifique o 'indice_camera' no config.json")
            break
        imagem = cv2.flip(imagem, 1)

        imagem = detector.encontrar_maos(imagem)
        lista_pontos = detector.encontrar_pontos(imagem)

        gesto_atual = detector.reconhecer_gesto(lista_pontos)
        gesto_confirmado = None

        if gesto_atual and "Deslizar" in gesto_atual:
            gesto_confirmado = gesto_atual
        elif gesto_atual == ultimo_gesto_detectado and gesto_atual is not None:
            contador_frames_gesto += 1
        else:
            contador_frames_gesto = 1
            ultimo_gesto_detectado = gesto_atual

        if contador_frames_gesto >= FRAMES_PARA_CONFIRMAR:
            gesto_confirmado = ultimo_gesto_detectado

        if gesto_confirmado and (time.time() - tempo_ultimo_comando > intervalo_comandos):
            acao_executada = False
            if gesto_confirmado == "Deslizar Direita":
                pyautogui.press('nexttrack')
                acao_executada = True
            elif gesto_confirmado == "Deslizar Esquerda":
                pyautogui.press('prevtrack')
                acao_executada = True
            elif gesto_confirmado == "Punho Fechado":
                pyautogui.press('playpause')
                acao_executada = True

            if acao_executada:
                print(f"Gesto Confirmado: {gesto_confirmado}")
                cv2.putText(imagem, gesto_confirmado, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                tempo_ultimo_comando = time.time()
                ultimo_gesto_detectado = None
                contador_frames_gesto = 0

        cv2.imshow("Captura", imagem)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()