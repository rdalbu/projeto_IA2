import cv2
import pyautogui
import time
import json
import os
from .hand_detector import DetectorMaos
from .ml_gesture import KerasGestureClassifier

def load_config(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Aviso: Arquivo '{os.path.basename(path)}' não encontrado. Usando configurações padrão.")
        return {}
    except json.JSONDecodeError:
        print(f"Erro: Falha ao decodificar '{os.path.basename(path)}'. Usando configurações padrão.")
        return {}

def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    config = load_config(config_path)

    cap = cv2.VideoCapture(config.get('indice_camera', 0))
    if not cap.isOpened():
        print(f"Erro: Não foi possível abrir a câmera com índice {config.get('indice_camera', 0)}.")
        return

    detector = DetectorMaos(
        deteccao_confianca=config.get('confianca_deteccao', 0.8),
        rastreio_confianca=config.get('confianca_rastreamento', 0.8)
    )

    ml_classifier = None
    if config.get("usar_modelo_gesto"):
        try:
            ml_classifier = KerasGestureClassifier(
                model_path=config.get("gesto_modelo_path", ""),
                labels=config.get("gesto_labels", []),
            )
            print("Classificador de gestos (Keras) carregado com sucesso.")
        except Exception as e:
            print(f"ERRO CRÍTICO ao carregar o modelo de gesto: {e}")
            print("Verifique se o caminho do modelo em 'config.json' está correto e se o arquivo existe.")
            return # Encerra o programa se o modelo não puder ser carregado
    else:
        print("Aviso: O uso do modelo de gesto está desabilitado em 'config.json'. O programa não fará nada.")
        return

    mapeamento_gestos = config.get("mapeamento_gestos", {})
    tempo_ultimo_comando = 0
    ultimo_gesto_detectado = None
    contador_frames_gesto = 0

    while True:
        sucesso, imagem = cap.read()
        if not sucesso:
            break
        
        imagem = cv2.flip(imagem, 1)
        imagem = detector.encontrar_maos(imagem)
        lista_pontos = detector.encontrar_pontos(imagem)

        gesto_atual = None
        if ml_classifier and lista_pontos:
            try:
                lbl, prob = ml_classifier.predict(lista_pontos, handedness='Right')
                if lbl and prob >= config.get("gesto_confianca_minima", 0.7):
                    gesto_atual = lbl
            except Exception as e:
                print(f"Erro durante a predição: {e}") # Adicionado para depuração
                gesto_atual = None
        
        # Lógica de confirmação de gesto
        if gesto_atual == ultimo_gesto_detectado and gesto_atual is not None:
            contador_frames_gesto += 1
        else:
            contador_frames_gesto = 1
        ultimo_gesto_detectado = gesto_atual
        
        gesto_confirmado = None
        if contador_frames_gesto >= config.get('frames_confirmacao_gesto', 5):
            gesto_confirmado = gesto_atual
            contador_frames_gesto = 0 # Reseta para evitar repetição imediata

        if gesto_confirmado and (time.time() - tempo_ultimo_comando > config.get('intervalo_entre_comandos_segundos', 1.0)):
            acao = mapeamento_gestos.get(gesto_confirmado)
            if acao:
                pyautogui.press(acao)
                print(f"Gesto Confirmado: {gesto_confirmado} -> Ação: {acao}")
                cv2.putText(imagem, gesto_confirmado, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                tempo_ultimo_comando = time.time()

        cv2.imshow("Captura de Gestos", imagem)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
