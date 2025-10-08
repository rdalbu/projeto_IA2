import math
import os

try:
    import tensorflow as tf  # Optional dependency
except Exception:  # pragma: no cover
    tf = None


def landmarks_to_features(landmarks, handedness='Right', include_z=False, mirror_x=True):
    """
    landmarks: lista de [id, x_px, y_px] (como retornado por DetectorMaos)
    Retorna um vetor Float32 normalizado similar ao usado no front-end.
    """
    if not landmarks or len(landmarks) < 21:
        return None

    # Recria estrutura simples com x,y,(z=0) em coordenadas relativas ao punho
    # Posição do punho (WRIST=0)
    wrist = landmarks[0]
    wx, wy = float(wrist[1]), float(wrist[2])

    # Espelha X se mão esquerda e mirror_x=True
    flip = -1.0 if (mirror_x and str(handedness).lower().startswith('left')) else 1.0

    pts = []
    for _, x, y in landmarks:
        rx = (float(x) - wx) * flip
        ry = (float(y) - wy)
        rz = 0.0  # Sem Z vindo do MediaPipe 2D aqui
        pts.append([rx, ry, rz])

    # Escala por maior alcance absoluto (x, y, z)
    max_range = 1e-6
    for x, y, z in pts:
        max_range = max(max_range, abs(x), abs(y), abs(z))
    for p in pts:
        p[0] /= max_range
        p[1] /= max_range
        p[2] /= max_range

    arr = []
    for x, y, z in pts:
        arr.append(x)
        arr.append(y)
        if include_z:
            arr.append(z)
    return arr  # lista de floats


class KerasGestureClassifier:
    def __init__(self, model_path, labels, include_z=False, mirror_x=True):
        if tf is None:
            raise RuntimeError("TensorFlow não está instalado. Instale 'tensorflow' para usar o classificador Keras.")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo não encontrado em: {model_path}")
        if not labels or not isinstance(labels, list):
            raise ValueError("'labels' precisa ser uma lista com a ordem das classes do modelo.")

        self.model = tf.keras.models.load_model(model_path)
        self.labels = labels
        self.include_z = include_z
        self.mirror_x = mirror_x

    def predict(self, landmarks, handedness='Right'):
        feat = landmarks_to_features(landmarks, handedness, self.include_z, self.mirror_x)
        if not feat:
            return None, 0.0
        x = tf.convert_to_tensor([feat], dtype=tf.float32)
        probs = self.model(x, training=False).numpy()[0]
        idx = int(max(range(len(probs)), key=lambda i: probs[i]))
        return self.labels[idx], float(probs[idx])

