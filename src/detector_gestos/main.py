import cv2
import pyautogui
import time
import json
import os
import serial
import threading
import queue
import numpy as np
import sounddevice as sd

from .hand_detector import DetectorMaos
from .ml_gesture import KerasGestureClassifier
from .kws_classifier import KwsClassifier

# --- Variáveis Globais ---
command_queue = queue.Queue()
audio_buffer = []
buffer_lock = threading.Lock()

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

def audio_callback(indata, frames, time, status):
    """Esta função é chamada pelo sounddevice para cada bloco de áudio."""
    if status:
        print(status)
    with buffer_lock:
        audio_buffer.append(indata.copy())

def process_audio_thread(kws_classifier, config):
    """Thread que processa o buffer de áudio e realiza a predição."""
    global audio_buffer
    min_confidence = config.get("kws_confianca_minima", 0.9)
    mapeamento_kws = config.get("mapeamento_kws", {})
    sample_rate = kws_classifier.sample_rate
    duration = kws_classifier.duration
    expected_length = int(sample_rate * duration)

    print("Thread de processamento de áudio iniciada.")
    while True:
        with buffer_lock:
            if len(audio_buffer) > 0:
                # Concatena os blocos de áudio do buffer
                data = np.concatenate(audio_buffer)
                audio_buffer.clear()
            else:
                data = None
        
        if data is not None and len(data) >= expected_length:
            # Pega o trecho mais recente correspondente à duração do modelo
            audio_segment = data[-expected_length:, 0]
            
            try:
                label, prob = kws_classifier.predict(audio_segment)
                if prob >= min_confidence and label not in ["neutro", "desconhecido"]:
                    acao = mapeamento_kws.get(label)
                    if acao:
                        print(f"Palavra-chave: {label} ({prob:.2f}) -> Colocando na fila: '{acao}'")
                        command_queue.put(acao)
            except Exception as e:
                print(f"Erro na predição de áudio: {e}")

        # Pequena pausa para não sobrecarregar a CPU
        time.sleep(0.5)


def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    config = load_config(config_path)

    ser = None
    if config.get('usar_serial', False):
        try:
            ser = serial.Serial(
                port=config.get('serial_port', 'COM5'),
                baudrate=config.get('serial_baudrate', 115200),
                timeout=1
            )
            print(f"Conectado à porta serial {config.get('serial_port', 'COM5')}.")
        except serial.SerialException as e:
            print(f"ERRO CRÍTICO ao conectar na porta serial: {e}")
            print("Verifique se a porta está correta no 'config.json' e se o ESP32 está conectado.")
            return

    # --- Inicialização do KWS (Áudio) ---
    kws_classifier = None
    audio_stream = None
    if config.get("usar_kws"):
        try:
            kws_classifier = KwsClassifier(
                model_path=config.get("kws_modelo_path"),
                labels_path=config.get("kws_labels_path")
            )
            
            audio_thread = threading.Thread(
                target=process_audio_thread, 
                args=(kws_classifier, config), 
                daemon=True
            )
            audio_thread.start()

            audio_stream = sd.InputStream(
                callback=audio_callback,
                samplerate=kws_classifier.sample_rate,
                channels=1,
                device=config.get("audio_input_device_index") # None para usar o padrão
            )
            audio_stream.start()
            print("Classificador de palavras-chave (KWS) carregado e stream de áudio iniciado.")

        except Exception as e:
            print(f"ERRO CRÍTICO ao inicializar o KWS: {e}")
            if ser: ser.close()
            return

    # --- Inicialização do Detector de Gestos (Vídeo) ---
    cap = None
    detector = None
    ml_classifier = None
    if config.get("usar_modelo_gesto"):
        cap = cv2.VideoCapture(config.get('indice_camera', 0))
        if not cap.isOpened():
            print(f"Erro: Não foi possível abrir a câmera com índice {config.get('indice_camera', 0)}.")
            if ser: ser.close()
            if audio_stream: audio_stream.stop()
            return

        detector = DetectorMaos(
            deteccao_confianca=config.get('confianca_deteccao', 0.8),
            rastreio_confianca=config.get('confianca_rastreamento', 0.8)
        )
        try:
            ml_classifier = KerasGestureClassifier(
                model_path=config.get("gesto_modelo_path", ""),
                labels=config.get("gesto_labels", []),
            )
            print("Classificador de gestos (Keras) carregado com sucesso.")
        except Exception as e:
            print(f"ERRO CRÍTICO ao carregar o modelo de gesto: {e}")
            if ser: ser.close()
            if audio_stream: audio_stream.stop()
            return
    else:
        print("Aviso: O uso do modelo de gesto está desabilitado em 'config.json'.")


    # --- Loop Principal ---
    mapeamento_gestos = config.get("mapeamento_gestos", {})
    tempo_ultimo_comando = 0
    ultimo_gesto_detectado = None
    contador_frames_gesto = 0

    print("\n--- Sistema iniciado. Pressione 'ESC' na janela de vídeo para sair. ---")

    while True:
        # --- Processamento de Vídeo ---
        if cap and ml_classifier:
            sucesso, imagem = cap.read()
            if not sucesso:
                break
            
            imagem = cv2.flip(imagem, 1)
            imagem = detector.encontrar_maos(imagem)
            lista_pontos = detector.encontrar_pontos(imagem)

            gesto_atual = None
            if lista_pontos:
                try:
                    lbl, prob = ml_classifier.predict(lista_pontos, handedness='Right')
                    if lbl and prob >= config.get("gesto_confianca_minima", 0.7):
                        gesto_atual = lbl
                except Exception as e:
                    print(f"Erro durante a predição de gesto: {e}")
            
            if gesto_atual == ultimo_gesto_detectado and gesto_atual is not None:
                contador_frames_gesto += 1
            else:
                contador_frames_gesto = 1
            ultimo_gesto_detectado = gesto_atual
            
            gesto_confirmado = None
            if contador_frames_gesto >= config.get('frames_confirmacao_gesto', 5):
                gesto_confirmado = gesto_atual
                contador_frames_gesto = 0

            if gesto_confirmado:
                acao = mapeamento_gestos.get(gesto_confirmado)
                if acao:
                    command_queue.put(acao)
                    print(f"Gesto: {gesto_confirmado} -> Colocando na fila: '{acao}'")
        else:
            # Se não houver câmera, cria uma imagem preta para a UI
            imagem = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(imagem, "Video desabilitado", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)


        # --- Processamento da Fila de Comandos (unificado para gestos e áudio) ---
        try:
            acao_pendente = command_queue.get_nowait()
            
            if time.time() - tempo_ultimo_comando > config.get('intervalo_entre_comandos_segundos', 1.0):
                if ser:
                    try:
                        ser.write(f'{acao_pendente}\n'.encode('utf-8'))
                        print(f"COMANDO -> Enviando via serial: '{acao_pendente}'")
                    except serial.SerialException as e:
                        print(f"Erro ao enviar comando serial: {e}")
                else:
                    pyautogui.press(acao_pendente)
                    print(f"COMANDO -> Ação local (pyautogui): '{acao_pendente}'")
                
                tempo_ultimo_comando = time.time()
                cv2.putText(imagem, f"Acao: {acao_pendente}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

        except queue.Empty:
            pass # Nada na fila, segue o baile

        cv2.imshow("Controle de Midia por IA", imagem)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    # --- Finalização ---
    print("\n--- Finalizando o sistema... ---")
    if audio_stream:
        audio_stream.stop()
        audio_stream.close()
        print("Stream de áudio fechado.")
    if cap:
        cap.release()
    cv2.destroyAllWindows()
    if ser:
        ser.close()
        print("Porta serial fechada.")

if __name__ == '__main__':
    main()
