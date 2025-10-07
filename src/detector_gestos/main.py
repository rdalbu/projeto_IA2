import cv2
import pyautogui
import time
import json
import os
from .hand_detector import DetectorMaos

def load_config():
    # O config.json está na raiz do projeto, então subimos dois níveis
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
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

def mapeia_gesto_para_acao(gesto, mapeamento_gestos):
    return mapeamento_gestos.get(gesto)

def main():
    config = load_config()
    if config is None:
        config = {
            "indice_camera": 0,
            "confianca_deteccao": 0.8,
            "confianca_rastreamento": 0.8,
            "sensibilidade_deslize_pixels": 70,
            "frames_confirmacao_gesto": 5,
            "intervalo_entre_comandos_segundos": 1.0,
            "mapeamento_gestos": {
                "Deslizar Direita": "nexttrack",
                "Deslizar Esquerda": "prevtrack",
                "Punho Fechado": "playpause"
            }
        }

    cap = cv2.VideoCapture(config['indice_camera'])
    detector = DetectorMaos(
        deteccao_confianca=config['confianca_deteccao'],
        rastreio_confianca=config['confianca_rastreamento'],
        swipe_threshold=config['sensibilidade_deslize_pixels']
    )

    mapeamento_gestos = config.get("mapeamento_gestos", {})

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
        if gesto_atual and ("Deslizar" in gesto_atual or gesto_atual == "Punho Fechado"):
            gesto_confirmado = gesto_atual
        elif gesto_atual == ultimo_gesto_detectado and gesto_atual is not None:
            contador_frames_gesto += 1
        else:
            contador_frames_gesto = 1
            ultimo_gesto_detectado = gesto_atual

        if contador_frames_gesto >= FRAMES_PARA_CONFIRMAR:
            gesto_confirmado = ultimo_gesto_detectado

        if gesto_confirmado and (time.time() - tempo_ultimo_comando > intervalo_comandos):
            acao = mapeia_gesto_para_acao(gesto_confirmado, mapeamento_gestos)
            if acao:
                pyautogui.press(acao)
                print(f"Gesto Confirmado: {gesto_confirmado} -> Ação: {acao}")
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
