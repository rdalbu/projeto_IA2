import os
import io
import json
import base64
import shutil
import tempfile
import subprocess
import numpy as np
import librosa
import soundfile as sf
from sklearn.model_selection import train_test_split
import keras
from keras.layers import Conv2D, MaxPooling2D, Dropout, Dense, Reshape, GlobalAveragePooling2D
from keras.utils import to_categorical
from keras.callbacks import EarlyStopping, ReduceLROnPlateau

INPUT_JSON_PATH = "kws-samples.json"
OUTPUT_MODEL_DIR = "models/kws"
OUTPUT_MODEL_NAME = "kws_model.h5"
OUTPUT_LABELS_NAME = "kws_labels.json"

TEST_SIZE = 0.2
VALIDATION_SIZE = 0.2
BATCH_SIZE = 32
EPOCHS = 50

_FFMPEG_AVAILABLE = shutil.which('ffmpeg') is not None

def _ffmpeg_webm_to_wav_bytes(webm_bytes: bytes, sr: int = 16000) -> bytes | None:
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f_in:
            in_path = f_in.name
            f_in.write(webm_bytes)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_out:
            out_path = f_out.name
        try:
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", in_path, "-ac", "1", "-ar", str(sr), out_path]
            subprocess.run(cmd, check=True)
            with open(out_path, "rb") as f:
                return f.read()
        finally:
            for p in (in_path, out_path):
                try:
                    os.remove(p)
                except Exception:
                    pass
    except FileNotFoundError:
        return None
    except Exception:
        return None

def _decode_wav_base64_to_mfcc(audio_b64: str, sr: int = 16000, duration: float = 1.0, n_mfcc: int = 13):
    try:
        s = (audio_b64 or "").strip()
        if "," in s:
            s = s.split(",", 1)[1]
        data = base64.b64decode(s)
        if len(data) >= 4 and data[:4] == b"\x1A\x45\xDF\xA3":
            wav_bytes = _ffmpeg_webm_to_wav_bytes(data, sr=sr)
            if not wav_bytes:
                return None
        else:
            wav_bytes = data
        try:
            y, sr0 = sf.read(io.BytesIO(wav_bytes), dtype='float32', always_2d=False)
            if isinstance(y, np.ndarray) and y.ndim == 2:
                y = y.mean(axis=0)
        except Exception:
            y, sr0 = librosa.load(io.BytesIO(wav_bytes), sr=None, mono=True)
        if sr0 != sr:
            y = librosa.resample(y, orig_sr=sr0, target_sr=sr)
        L = int(sr * duration)
        if len(y) < L:
            y = np.pad(y, (0, L - len(y)), mode='constant')
        else:
            y = y[:L]
        return librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    except Exception:
        return None

def load_data_from_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    labels = data.get('classes') or data.get('labels')
    samples = data.get('samples') or []
    if not labels or not isinstance(samples, list):
        raise ValueError("JSON inválido: esperado chaves 'classes' e 'samples'.")
    uses_spectrogram = (len(samples) > 0) and ('spectrogram' in samples[0])
    uses_audio_b64 = (len(samples) > 0) and ('audioBase64' in samples[0])
    is_webm = False
    if uses_audio_b64 and len(samples) > 0:
        try:
            b64 = (samples[0].get('audioBase64') or '').split(',', 1)[-1]
            hdr = base64.b64decode(b64)[:4]
            is_webm = hdr == b"\x1A\x45\xDF\xA3"
        except Exception:
            is_webm = False
    if uses_audio_b64 and is_webm and not _FFMPEG_AVAILABLE:
        raise SystemExit("Dataset usa audioBase64 WebM/Opus e ffmpeg não está no PATH.")
    X_list, y_labels = [], []
    if uses_spectrogram:
        for s in samples:
            X_list.append(np.array(s['spectrogram'], dtype=np.float32))
            y_labels.append(s['label'])
        if X_list and getattr(X_list[0], 'ndim', 0) == 2:
            target_w = int(X_list[0].shape[1])
            X_list = [x[:, :target_w] if x.shape[1] >= target_w else np.pad(x, ((0,0),(0, target_w - x.shape[1])), mode='constant') for x in X_list]
    elif uses_audio_b64:
        for s in samples:
            mfcc = _decode_wav_base64_to_mfcc(s.get('audioBase64', ''))
            if mfcc is None:
                continue
            X_list.append(mfcc.astype(np.float32))
            y_labels.append(s['label'])
        if not X_list:
            raise ValueError("Falha ao decodificar amostras de áudio base64.")
        target_w = X_list[0].shape[1]
        X_list = [x[:, :target_w] if x.shape[1] >= target_w else np.pad(x, ((0,0),(0, target_w - x.shape[1])), mode='constant') for x in X_list]
    else:
        raise ValueError("Formato não reconhecido: espectrogram ou audioBase64.")
    X = np.stack(X_list, axis=0).astype(np.float32)
    label_to_int = {label: i for i, label in enumerate(labels)}
    y = np.array([label_to_int[lbl] for lbl in y_labels], dtype=np.int64)
    os.makedirs(OUTPUT_MODEL_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_MODEL_DIR, OUTPUT_LABELS_NAME), 'w', encoding='utf-8') as f:
        json.dump({i: label for i, label in enumerate(labels)}, f, ensure_ascii=False)
    return X, y, labels

def build_model(input_shape, num_classes):
    h, w = int(input_shape[0]), int(input_shape[1])
    model = keras.Sequential([
        keras.layers.Input(shape=(h, w)),
        Reshape((h, w, 1)),
        Conv2D(8, (2, 2), activation='relu'),
        MaxPooling2D((2, 2), strides=(2, 2)),
        Conv2D(16, (2, 2), activation='relu'),
        MaxPooling2D((2, 2), strides=(2, 2)),
        GlobalAveragePooling2D(),
        Dropout(0.25),
        Dense(64, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

def main():
    if not os.path.exists(INPUT_JSON_PATH):
        print(f"ERRO: '{INPUT_JSON_PATH}' não encontrado.")
        return
    X, y, labels = load_data_from_json(INPUT_JSON_PATH)
    if len(X) == 0:
        print("Nenhum dado no dataset.")
        return
    num_classes = len(labels)
    y_cat = to_categorical(y, num_classes=num_classes)
    X_train, X_test, y_train, y_test = train_test_split(X, y_cat, test_size=TEST_SIZE, stratify=y, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=VALIDATION_SIZE, stratify=y_train, random_state=42)
    model = build_model(X_train.shape[1:], num_classes)
    callbacks = [EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True), ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=1e-4)]
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, validation_data=(X_val, y_val), callbacks=callbacks)
    model_path = os.path.join(OUTPUT_MODEL_DIR, OUTPUT_MODEL_NAME)
    model.save(model_path)
    try:
        out_dir = os.path.join(os.path.dirname(OUTPUT_MODEL_DIR), 'kws_web')
        os.makedirs(out_dir, exist_ok=True)
        shutil.copy(os.path.join(OUTPUT_MODEL_DIR, OUTPUT_LABELS_NAME), out_dir)
        try:
            from tensorflowjs.converters import save_keras_model
            save_keras_model(model, out_dir)
        except Exception:
            os.system(f'tensorflowjs_converter --input_format=keras {model_path} {out_dir}')
    except Exception:
        pass
    print("Treinamento concluído.")

if __name__ == '__main__':
    main()
