import cv2
import pyautogui
import time
import json
import os
from .hand_detector import DetectorMaos
from .gesture_recognizer import GestureRecognizer

def load_config(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Aviso: Arquivo config.json não encontrado. Usando configurações padrão.")
        return {}
    except json.JSONDecodeError:
        print("Erro: Falha ao decodificar config.json. Verifique a formatação. Usando configurações padrão.")
        return {}

def validate_config(user_config):
    default_config = {
        "indice_camera": 0,
        "confianca_deteccao": 0.8,
        "confianca_rastreamento": 0.8,
        "sensibilidade_deslize_pixels": 70,
        "pinch_threshold_pixels": 30,
        "frames_confirmacao_gesto": 5,
        "intervalo_entre_comandos_segundos": 1.0,
        "mapeamento_gestos": {
            "Deslizar Direita": "nexttrack",
            "Deslizar Esquerda": "prevtrack",
            "Pinca": "playpause"
        }
    }
    
    config = default_config
    config.update(user_config)

    if not isinstance(config["indice_camera"], int) or config["indice_camera"] < 0:
        print(f"Aviso: 'indice_camera' inválido ({config['indice_camera']}). Usando padrão: {default_config['indice_camera']}.")
        config["indice_camera"] = default_config["indice_camera"]

    if not isinstance(config["confianca_deteccao"], float) or not (0.0 <= config["confianca_deteccao"] <= 1.0):
        print(f"Aviso: 'confianca_deteccao' inválida. Usando padrão: {default_config['confianca_deteccao']}.")
        config["confianca_deteccao"] = default_config["confianca_deteccao"]

    return config

def processa_gesto(gesto_atual, ultimo_gesto, contador_frames, frames_para_confirmar):
    if gesto_atual and ("Deslizar" in gesto_atual or gesto_atual == "Pinca"):
        return gesto_atual, gesto_atual, 1

    if gesto_atual == ultimo_gesto and gesto_atual is not None:
        contador_frames += 1
    else:
        contador_frames = 1
    
    gesto_confirmado = None
    if contador_frames >= frames_para_confirmar:
        gesto_confirmado = gesto_atual

    return gesto_confirmado, gesto_atual, contador_frames

def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    user_config = load_config(config_path)
    config = validate_config(user_config)

    cap = cv2.VideoCapture(config['indice_camera'])
    if not cap.isOpened():
        print(f"Erro: Não foi possível abrir a câmera com índice {config['indice_camera']}.")
        return

    detector = DetectorMaos(
        deteccao_confianca=config['confianca_deteccao'],
        rastreio_confianca=config['confianca_rastreamento']
    )
    recognizer = GestureRecognizer(
        swipe_threshold=config['sensibilidade_deslize_pixels'],
        pinch_threshold=config.get('pinch_threshold_pixels', 30)
    )

    mapeamento_gestos = config.get("mapeamento_gestos", {})
    tempo_ultimo_comando = 0
    ultimo_gesto_detectado = None
    contador_frames_gesto = 0

    while True:
        sucesso, imagem = cap.read()
        if not sucesso:
            print("Erro: Falha ao ler o frame da câmera.")
            break
        
        imagem = cv2.flip(imagem, 1)
        imagem = detector.encontrar_maos(imagem)
        lista_pontos = detector.encontrar_pontos(imagem)

        recognizer.update_history(lista_pontos)
        gesto_atual = recognizer.recognize_gesture(lista_pontos)
        
        gesto_confirmado, ultimo_gesto_detectado, contador_frames_gesto = processa_gesto(
            gesto_atual, ultimo_gesto_detectado, contador_frames_gesto, config['frames_confirmacao_gesto']
        )

        if gesto_confirmado and (time.time() - tempo_ultimo_comando > config['intervalo_entre_comandos_segundos']):
            acao = mapeamento_gestos.get(gesto_confirmado)
            if acao:
                pyautogui.press(acao)
                print(f"Gesto Confirmado: {gesto_confirmado} -> Ação: {acao}")
                cv2.putText(imagem, gesto_confirmado, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                tempo_ultimo_comando = time.time()
                ultimo_gesto_detectado = None
                contador_frames_gesto = 0

        cv2.imshow("Captura de Gestos", imagem)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
