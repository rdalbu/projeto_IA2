import os
import time
import json
import cv2
import numpy as np

from .hand_detector import DetectorMaos
from .ml_gesture import landmarks_to_features

try:
    import tensorflow as tf
except Exception as e:
    tf = None


def load_config(root_dir):
    cfg_path = os.path.join(root_dir, 'config.json')
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def build_model(input_dim, num_classes):
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(input_dim,)),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dropout(0.1),
        tf.keras.layers.Dense(num_classes, activation='softmax'),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])
    return model


def main():
    if tf is None:
        print("Erro: TensorFlow não está instalado. Execute 'pip install tensorflow' e tente novamente.")
        return

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    cfg = load_config(root)

    labels = cfg.get('gesto_labels') or []
    if not labels:
        print("Defina 'gesto_labels' no config.json, ex.: ['Pinca','Deslizar Direita','Deslizar Esquerda','Mao Aberta']")
        return

    include_z = bool(cfg.get('gesto_include_z', False))
    mirror_x = bool(cfg.get('gesto_mirror_x', True))
    model_out = cfg.get('gesto_modelo_path') or os.path.join(root, 'models', 'gesture_keras')
    os.makedirs(os.path.dirname(model_out), exist_ok=True)

    print("Treinador de Gestos (MediaPipe + TF/Keras)")
    print(f"Classes: {labels}")
    print("Controles:\n  [1..9] seleciona classe atual\n  [A] adiciona amostra do frame atual\n  [R] grava 2s de amostras\n  [T] treina\n  [S] salva modelo\n  [ESC] sair")

    cap = cv2.VideoCapture(int(cfg.get('indice_camera', 0)))
    if not cap.isOpened():
        print("Falha ao abrir câmera.")
        return

    det = DetectorMaos(deteccao_confianca=float(cfg.get('confianca_deteccao', 0.8)),
                       rastreio_confianca=float(cfg.get('confianca_rastreamento', 0.8)))

    X, y = [], []
    cur_label_idx = 0
    model = None

    def status_text():
        counts = [sum(1 for t in y if t == i) for i in range(len(labels))]
        return f"Classe: {labels[cur_label_idx]} | Amostras: {counts}"

    last_info = ''
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        vis = det.encontrar_maos(frame.copy())
        pts = det.encontrar_pontos(vis)

        cv2.putText(vis, status_text(), (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        if last_info:
            cv2.putText(vis, last_info, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

        cv2.imshow('Treino de Gestos', vis)
        k = cv2.waitKey(1) & 0xFF
        if k == 27:  # ESC
            break
        if k in range(ord('1'), ord('9')+1):
            idx = k - ord('1')
            if 0 <= idx < len(labels):
                cur_label_idx = idx
        elif k in (ord('a'), ord('A')):
            feat = landmarks_to_features(pts, 'Right', include_z, mirror_x)
            if feat:
                X.append(feat)
                y.append(cur_label_idx)
                last_info = f"Amostra adicionada: {labels[cur_label_idx]} (total={len(y)})"
        elif k in (ord('r'), ord('R')):
            t_end = time.time() + 2.0
            n_rec = 0
            while time.time() < t_end:
                ok2, fr2 = cap.read()
                if not ok2:
                    break
                fr2 = cv2.flip(fr2, 1)
                det.encontrar_maos(fr2)
                pts2 = det.encontrar_pontos(fr2)
                feat = landmarks_to_features(pts2, 'Right', include_z, mirror_x)
                if feat:
                    X.append(feat)
                    y.append(cur_label_idx)
                    n_rec += 1
                cv2.putText(fr2, f"Gravando {labels[cur_label_idx]}...", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
                cv2.imshow('Treino de Gestos', fr2)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
            last_info = f"Gravação concluída: {n_rec} amostras para {labels[cur_label_idx]}"
        elif k in (ord('t'), ord('T')):
            if not X:
                last_info = "Nenhuma amostra coletada."
            else:
                Xn = np.array(X, dtype=np.float32)
                yn = np.array(y, dtype=np.int64)
                input_dim = Xn.shape[1]
                model = build_model(input_dim, len(labels))
                hist = model.fit(Xn, yn, epochs=25, batch_size=32, validation_split=0.15, verbose=0)
                acc = float(hist.history['accuracy'][-1])
                last_info = f"Treino ok. acc={acc:.2f}"
        elif k in (ord('s'), ord('S')):
            if model is None:
                last_info = "Treine antes de salvar."
            else:
                # Salva em SavedModel (diretório) ou .h5 se path terminar com .h5
                p = model_out
                if p.lower().endswith('.h5'):
                    model.save(p)
                else:
                    tf.keras.models.save_model(model, p, overwrite=True)
                last_info = f"Modelo salvo em: {p}"

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()

