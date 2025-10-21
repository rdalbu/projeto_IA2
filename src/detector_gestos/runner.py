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

# Envio de teclas de mídia no Windows
try:
    import platform
    import ctypes
    _IS_WINDOWS = platform.system().lower().startswith('win')
except Exception:
    _IS_WINDOWS = False

VK_MEDIA = {
    'playpause': 0xB3,
    'nexttrack': 0xB0,
    'prevtrack': 0xB1,
}


def send_media_key_local(action: str):
    if _IS_WINDOWS and action in VK_MEDIA:
        try:
            vk = VK_MEDIA[action]
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
            return True
        except Exception:
            return False
    try:
        pyautogui.press(action)
        return True
    except Exception:
        return False


class GestureRunner:
    def __init__(self, config_path, on_event=None):
        self.config_path = config_path
        self.on_event = on_event or (lambda evt: None)

        self._thread = None
        self._stop = threading.Event()
        self._audio_thread = None

        self.command_queue = queue.Queue()
        self.audio_buffer = []
        self.buffer_lock = threading.Lock()

        self.ser = None
        self.audio_stream = None
        self.cap = None
        self.detector = None
        self.ml_classifier = None
        self.kws_classifier = None
        self.kws_enabled = False
        self.output_mode = "auto"  # auto|serial|local
        # preview frames
        self._frame_lock = threading.Lock()
        self._last_jpeg = None
        self.preview_overlay = True
        self._last_preview_ts = 0.0
        self._preview_interval = 1.0 / 15.0
        self.jpeg_quality = 70

        self.config = {}

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception:
            self.config = {}

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(status)
        with self.buffer_lock:
            self.audio_buffer.append(indata.copy())

    def _process_audio_thread(self):
        cfg = self.config
        min_conf = cfg.get("kws_confianca_minima", 0.9)
        mapeamento = cfg.get("mapeamento_kws", {})
        sample_rate = self.kws_classifier.sample_rate
        duration = self.kws_classifier.duration
        expected_length = int(sample_rate * duration)

        while not self._stop.is_set():
            if not self.kws_enabled or self.kws_classifier is None:
                time.sleep(0.2)
                continue
            with self.buffer_lock:
                data = np.concatenate(self.audio_buffer) if self.audio_buffer else None
                self.audio_buffer.clear()

            if data is not None and len(data) >= expected_length:
                audio_segment = data[-expected_length:, 0]
                try:
                    label, prob = self.kws_classifier.predict(audio_segment)
                    if prob >= min_conf and label not in ["neutro", "desconhecido"]:
                        acao = mapeamento.get(label)
                        if acao:
                            self.on_event({
                                "type": "kws",
                                "label": label,
                                "prob": float(prob),
                                "action": acao,
                                "ts": time.time(),
                            })
                            self.command_queue.put(acao)
                except Exception as e:
                    print(f"Erro na predição de áudio: {e}")

            time.sleep(0.3)

    def start(self):
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        # parar áudio stream
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except Exception:
                pass
            self.audio_stream = None
        # liberar câmera
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        # fechar serial
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def is_running(self):
        return bool(self._thread and self._thread.is_alive())

    def set_output_mode(self, mode: str):
        mode = (mode or "").lower()
        if mode in ("auto", "serial", "local"):
            self.output_mode = mode
            return True
        return False

    def get_output_state(self):
        return {
            "mode": self.output_mode,
            "serial_available": bool(self.ser),
        }

    def get_last_frame(self):
        with self._frame_lock:
            return self._last_jpeg

    def enable_kws(self) -> bool:
        if self.kws_enabled:
            return True
        cfg = self.config
        try:
            mp = cfg.get("kws_modelo_path")
            lp = cfg.get("kws_labels_path")
            if not mp or not os.path.exists(mp):
                raise FileNotFoundError(f"Modelo KWS não encontrado: {mp}")
            if not lp or not os.path.exists(lp):
                raise FileNotFoundError(f"Labels KWS não encontrado: {lp}")
            # iniciar classificador se necessário
            if self.kws_classifier is None:
                self.kws_classifier = KwsClassifier(mp, lp)
            # iniciar thread de áudio se necessário
            if not self._audio_thread or not self._audio_thread.is_alive():
                self._audio_thread = threading.Thread(target=self._process_audio_thread, daemon=True)
                self._audio_thread.start()
            # iniciar stream
            if not self.audio_stream:
                self.audio_stream = sd.InputStream(
                    callback=self._audio_callback,
                    samplerate=self.kws_classifier.sample_rate,
                    channels=1,
                    device=cfg.get("audio_input_device_index"),
                )
                self.audio_stream.start()
            self.kws_enabled = True
            return True
        except Exception as e:
            print("Falha ao habilitar KWS:", e)
            self.kws_enabled = False
            return False

    def disable_kws(self) -> bool:
        self.kws_enabled = False
        try:
            if self.audio_stream:
                try:
                    self.audio_stream.stop()
                    self.audio_stream.close()
                except Exception:
                    pass
                self.audio_stream = None
            # opcionalmente manter classificador instanciado
            return True
        finally:
            return True

    def _run(self):
        self._load_config()
        cfg = self.config
        # preview config
        try:
            max_fps = float(cfg.get('preview_max_fps', 15))
            self._preview_interval = 1.0 / max(1.0, max_fps)
        except Exception:
            self._preview_interval = 1.0 / 15.0
        try:
            self.jpeg_quality = int(cfg.get('jpeg_quality', 70))
        except Exception:
            self.jpeg_quality = 70

        # Serial opcional
        self.ser = None
        if cfg.get('usar_serial', False):
            try:
                self.ser = serial.Serial(
                    port=cfg.get('serial_port', 'COM5'),
                    baudrate=cfg.get('serial_baudrate', 115200),
                    timeout=1,
                )
                print(f"Conectado à porta serial {cfg.get('serial_port', 'COM5')}.")
            except serial.SerialException as e:
                print(f"Aviso: falha ao abrir serial: {e}. Usando pyautogui.")
                self.ser = None
        # defina modo de saída inicial
        self.output_mode = "serial" if self.ser else "local"

        # KWS opcional
        self.kws_classifier = None
        self.audio_stream = None
        if cfg.get("usar_kws"):
            try:
                mp = cfg.get("kws_modelo_path")
                lp = cfg.get("kws_labels_path")
                if not mp or not os.path.exists(mp):
                    raise FileNotFoundError(f"Modelo KWS não encontrado: {mp}")
                if not lp or not os.path.exists(lp):
                    raise FileNotFoundError(f"Labels KWS não encontrado: {lp}")
                self.kws_classifier = KwsClassifier(mp, lp)
                self._audio_thread = threading.Thread(target=self._process_audio_thread, daemon=True)
                self._audio_thread.start()
                self.audio_stream = sd.InputStream(
                    callback=self._audio_callback,
                    samplerate=self.kws_classifier.sample_rate,
                    channels=1,
                    device=cfg.get("audio_input_device_index"),
                )
                self.audio_stream.start()
                self.kws_enabled = True
                print("KWS iniciado.")
            except Exception as e:
                print("Aviso: KWS desabilitado:", e)
                self.kws_classifier = None
                self.kws_enabled = False

        # Gestos opcional (sem janela)
        self.cap = None
        self.detector = None
        self.ml_classifier = None
        if cfg.get("usar_modelo_gesto"):
            cam_index = cfg.get('indice_camera', 0)
            self.cap = cv2.VideoCapture(cam_index)
            if not self.cap.isOpened():
                print(f"Aviso: falha ao abrir camera idx {cfg.get('indice_camera', 0)}. Gestos desabilitados.")
                self.cap = None
            else:
                # Tenta definir resolução e fps
                try:
                    w = int(cfg.get('camera_width', 640))
                    h = int(cfg.get('camera_height', 480))
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                    target_fps = float(cfg.get('camera_fps', 30))
                    self.cap.set(cv2.CAP_PROP_FPS, target_fps)
                except Exception:
                    pass
                self.detector = DetectorMaos(
                    deteccao_confianca=cfg.get('confianca_deteccao', 0.8),
                    rastreio_confianca=cfg.get('confianca_rastreamento', 0.8),
                )
                try:
                    self.ml_classifier = KerasGestureClassifier(
                        model_path=cfg.get("gesto_modelo_path", ""),
                        labels=cfg.get("gesto_labels", []),
                    )
                    print("Classificador de gestos iniciado.")
                except Exception as e:
                    print("Aviso: Gestos desabilitados:", e)
                    self.ml_classifier = None

        mapeamento_gestos = cfg.get("mapeamento_gestos", {})
        tempo_ultimo = 0.0
        ultimo_lbl = None
        frames_ok = 0
        min_prob = cfg.get("gesto_confianca_minima", 0.7)
        cooldown = float(cfg.get('intervalo_entre_comandos_segundos', 1.0))
        next_allowed_ts = 0.0

        while not self._stop.is_set():
            imagem = None

            if self.cap:
                ok, imagem = self.cap.read()
                if not ok:
                    break
                imagem = cv2.flip(imagem, 1)
                if self.detector:
                    imagem = self.detector.encontrar_maos(imagem, desenho=self.preview_overlay)
                    pts = self.detector.encontrar_pontos(imagem)
                else:
                    pts = []
                # atualiza frame preview
                try:
                    now = time.time()
                    if (now - self._last_preview_ts) >= self._preview_interval:
                        params = [int(cv2.IMWRITE_JPEG_QUALITY), int(self.jpeg_quality)]
                        ok_jpg, buf = cv2.imencode('.jpg', imagem, params)
                        if ok_jpg:
                            with self._frame_lock:
                                self._last_jpeg = buf.tobytes()
                            self._last_preview_ts = now
                except Exception:
                    pass

                lbl = None
                prob = 0.0
                has_pts = bool(pts)
                if has_pts and self.ml_classifier and self.detector:
                    try:
                        handed = self.detector.get_handedness(0)
                        lbl, prob = self.ml_classifier.predict(pts, handedness=handed or 'Right')
                    except Exception as e:
                        print("Erro predição gesto:", e)
                        lbl, prob = None, 0.0

                atual = lbl if (lbl and prob >= min_prob) else None
                if atual == ultimo_lbl and atual is not None:
                    frames_ok += 1
                else:
                    frames_ok = 1
                ultimo_lbl = atual

                if frames_ok >= cfg.get('frames_confirmacao_gesto', 5):
                    frames_ok = 0
                    if atual:
                        acao = mapeamento_gestos.get(atual)
                        if acao:
                            now = time.time()
                            if now >= next_allowed_ts:
                                # enfileira com dados para log no momento da execução
                                self.command_queue.put({
                                    'acao': acao,
                                    'label': atual,
                                    'prob': float(prob),
                                    'ts': now,
                                })
                                next_allowed_ts = now + cooldown

            # envio de comandos
            try:
                item = self.command_queue.get_nowait()
                # item pode ser string (compat) ou dict com metadados
                if isinstance(item, dict):
                    acao = item.get('acao')
                    meta = item
                else:
                    acao = item
                    meta = {'acao': acao, 'label': None, 'prob': 0.0, 'ts': time.time()}

                if time.time() - tempo_ultimo > cooldown:
                    chosen = self.output_mode
                    if chosen == "auto":
                        chosen = "serial" if self.ser else "local"
                    if chosen == "serial" and self.ser:
                        try:
                            self.ser.write(f"{acao}\n".encode('utf-8'))
                            print(f"SERIAL -> {acao}")
                        except serial.SerialException as e:
                            print("Erro serial:", e)
                    else:
                        ok_local = send_media_key_local(acao)
                        print(f"LOCAL -> {acao}{'' if ok_local else ' (fallback falhou)'}")
                    tempo_ultimo = time.time()
                    # agora sim: publica evento de ação executada (reduz log spam)
                    self.on_event({
                        'type': 'gesture',
                        'label': meta.get('label'),
                        'prob': meta.get('prob', 0.0),
                        'action': acao,
                        'ts': tempo_ultimo,
                    })
            except queue.Empty:
                pass

            time.sleep(0.01)

