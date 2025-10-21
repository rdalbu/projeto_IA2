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


def load_config(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def send_local(action):
    try:
        pyautogui.press(action)
        return True
    except Exception:
        return False


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    cfg = load_config(os.path.join(root, 'config.json'))

    ser = None
    if cfg.get('usar_serial', False):
        try:
            ser = serial.Serial(
                port=cfg.get('serial_port', 'COM5'),
                baudrate=cfg.get('serial_baudrate', 115200),
                timeout=1,
            )
        except serial.SerialException:
            ser = None

    kws_classifier = None
    audio_stream = None
    command_queue = queue.Queue()
    audio_buffer = []
    buffer_lock = threading.Lock()

    def audio_callback(indata, frames, time_info, status):
        if status:
            pass
        with buffer_lock:
            audio_buffer.append(indata.copy())

    def process_audio_thread():
        min_conf = float(cfg.get('kws_confianca_minima', 0.9))
        mapping = cfg.get('mapeamento_kws', {})
        sr = kws_classifier.sample_rate
        dur = kws_classifier.duration
        exp_len = int(sr * dur)
        while True:
            with buffer_lock:
                data = np.concatenate(audio_buffer) if audio_buffer else None
                audio_buffer.clear()
            if data is not None and len(data) >= exp_len:
                segment = data[-exp_len:, 0]
                try:
                    label, prob = kws_classifier.predict(segment)
                    if prob >= min_conf and label not in ['neutro', 'desconhecido']:
                        act = mapping.get(label)
                        if act:
                            command_queue.put(act)
                except Exception:
                    pass
            time.sleep(0.3)

    if bool(cfg.get('usar_kws')):
        try:
            mp = cfg.get('kws_modelo_path')
            lp = cfg.get('kws_labels_path')
            if mp and lp and os.path.exists(mp) and os.path.exists(lp):
                kws_classifier = KwsClassifier(mp, lp)
                t = threading.Thread(target=process_audio_thread, daemon=True)
                t.start()
                audio_stream = sd.InputStream(
                    callback=audio_callback,
                    samplerate=kws_classifier.sample_rate,
                    channels=1,
                    device=cfg.get('audio_input_device_index'),
                )
                audio_stream.start()
        except Exception:
            kws_classifier = None
            audio_stream = None

    cap = None
    detector = None
    ml = None
    if cfg.get('usar_modelo_gesto'):
        cap = cv2.VideoCapture(int(cfg.get('indice_camera', 0)))
        if cap.isOpened():
            try:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(cfg.get('camera_width', 640)))
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(cfg.get('camera_height', 480)))
                cap.set(cv2.CAP_PROP_FPS, float(cfg.get('camera_fps', 30)))
            except Exception:
                pass
            detector = DetectorMaos(
                deteccao_confianca=float(cfg.get('confianca_deteccao', 0.8)),
                rastreio_confianca=float(cfg.get('confianca_rastreamento', 0.8)),
            )
            try:
                ml = KerasGestureClassifier(
                    model_path=cfg.get('gesto_modelo_path', ''),
                    labels=cfg.get('gesto_labels', []),
                )
            except Exception:
                ml = None

    mapping_g = cfg.get('mapeamento_gestos', {})
    min_prob = float(cfg.get('gesto_confianca_minima', 0.7))
    confirm_frames = int(cfg.get('frames_confirmacao_gesto', 5))
    cooldown = float(cfg.get('intervalo_entre_comandos_segundos', 1.0))

    last_lbl = None
    frames_ok = 0
    last_cmd_ts = 0.0

    while True:
        frame = None
        if cap and cap.isOpened():
            ok, img = cap.read()
            if not ok:
                break
            img = cv2.flip(img, 1)
            if detector:
                vis = detector.encontrar_maos(img.copy())
                pts = detector.encontrar_pontos(vis)
            else:
                vis = img
                pts = []
            lbl, prob = None, 0.0
            if pts and ml:
                try:
                    handed = detector.get_handedness(0)
                    lbl, prob = ml.predict(pts, handedness=handed or 'Right')
                except Exception:
                    lbl, prob = None, 0.0
            cur = lbl if (lbl and prob >= min_prob) else None
            if cur == last_lbl and cur is not None:
                frames_ok += 1
            else:
                frames_ok = 1
            last_lbl = cur
            act = None
            if frames_ok >= confirm_frames:
                frames_ok = 0
                if cur:
                    act = mapping_g.get(cur)
                    if act:
                        command_queue.put(act)
            try:
                cmd = command_queue.get_nowait()
                if time.time() - last_cmd_ts > cooldown:
                    if ser:
                        try:
                            ser.write(f"{cmd}\n".encode('utf-8'))
                        except serial.SerialException:
                            pass
                    else:
                        send_local(cmd)
                    last_cmd_ts = time.time()
            except queue.Empty:
                pass
            cv2.imshow('Gestures', vis)
            if cv2.waitKey(1) & 0xFF == 27:
                break
        else:
            time.sleep(0.1)

    if audio_stream:
        try:
            audio_stream.stop()
            audio_stream.close()
        except Exception:
            pass
    if cap:
        cap.release()
    cv2.destroyAllWindows()
    if ser:
        try:
            ser.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()

