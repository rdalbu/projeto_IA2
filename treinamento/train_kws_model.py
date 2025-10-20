import os
import io
import base64
import numpy as np
import json
import shutil
from sklearn.model_selection import train_test_split
import keras
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, Reshape
from keras.utils import to_categorical
from keras.callbacks import EarlyStopping, ReduceLROnPlateau
import librosa
import soundfile as sf
import subprocess
import tempfile

# Aceita tanto o formato com espectrogramas prontos (samples[].spectrogram)
# quanto o formato com áudio em base64 (samples[].audioBase64).
INPUT_JSON_PATH = "kws-samples.json"
OUTPUT_MODEL_DIR = "models/kws"
OUTPUT_MODEL_NAME = "kws_model.h5"
OUTPUT_LABELS_NAME = "kws_labels.json"

TEST_SIZE = 0.2
VALIDATION_SIZE = 0.2
BATCH_SIZE = 32
EPOCHS = 50

_FFMPEG_AVAILABLE = shutil.which('ffmpeg') is not None
_FFMPEG_WARNED = False

def _ffmpeg_webm_to_wav_bytes(webm_bytes: bytes, sr: int = 16000) -> bytes | None:
    """Converte bytes WebM/Opus para WAV PCM mono em sr especificada via ffmpeg.
    Retorna bytes do WAV ou None se falhar/ffmpeg ausente.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f_in:
            in_path = f_in.name
            f_in.write(webm_bytes)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_out:
            out_path = f_out.name
        try:
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", in_path,
                "-ac", "1",  # mono
                "-ar", str(sr),  # sample rate
                out_path,
            ]
            subprocess.run(cmd, check=True)
            with open(out_path, "rb") as f:
                return f.read()
        finally:
            # limpeza silenciosa
            try:
                os.remove(in_path)
            except Exception:
                pass
            try:
                os.remove(out_path)
            except Exception:
                pass
    except FileNotFoundError:
        # Silencioso aqui; a checagem principal ocorre antes do loop
        return None
    except Exception as e:
        print("Aviso: falha na convers\u00e3o WebM via ffmpeg:", e)
        return None


def _decode_wav_base64_to_mfcc(audio_b64: str, sr: int = 16000, duration: float = 1.0, n_mfcc: int = 13):
    # audio_b64 pode vir no formato data:audio/wav;base64,<payload>
    try:
        audio_b64 = (audio_b64 or "").strip()
        if "," in audio_b64:
            audio_b64 = audio_b64.split(",", 1)[1]
        wav_or_webm_bytes = base64.b64decode(audio_b64)
        # Detecta WebM/Matroska (EBML) por cabeçalho 0x1A45DFA3 (base64 típico inicia com GkXf...)
        if len(wav_or_webm_bytes) >= 4 and wav_or_webm_bytes[:4] == b"\x1A\x45\xDF\xA3":
            # Converter via ffmpeg
            wav_bytes = _ffmpeg_webm_to_wav_bytes(wav_or_webm_bytes, sr=sr)
            if not wav_bytes:
                return None
        else:
            wav_bytes = wav_or_webm_bytes

        # 1) Tenta com soundfile (mais robusto para BytesIO)
        try:
            y, sr0 = sf.read(io.BytesIO(wav_bytes), dtype='float32', always_2d=False)
            if y is None:
                return None
            # Se estéreo, converte para mono
            if isinstance(y, np.ndarray) and y.ndim == 2:
                if y.shape[0] == 2:
                    y = y.mean(axis=0)
                else:
                    y = y.mean(axis=1)
        except Exception:
            # 2) Fallback: audioread/librosa.load
            y, sr0 = librosa.load(io.BytesIO(wav_bytes), sr=None, mono=True)

        # Resample para sr desejada
        if sr0 != sr:
            y = librosa.resample(y, orig_sr=sr0, target_sr=sr)

        expected_len = int(sr * duration)
        if len(y) < expected_len:
            y = np.pad(y, (0, expected_len - len(y)), mode='constant')
        else:
            y = y[:expected_len]
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
        return mfcc
    except Exception:
        return None


def load_data_from_json(json_path):
    print(f"Carregando dataset de '{json_path}'...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    labels = data.get('classes') or data.get('labels')
    samples = data.get('samples') or []
    if not labels or not isinstance(samples, list):
        raise ValueError("JSON de dataset inválido: esperado chaves 'classes' e 'samples'.")

    # Detecta formato dos samples
    uses_spectrogram = (len(samples) > 0) and ('spectrogram' in samples[0])
    uses_audio_b64 = (len(samples) > 0) and ('audioBase64' in samples[0])

    # Probing de header para audioBase64
    is_webm = False
    if uses_audio_b64 and len(samples) > 0:
        try:
            probe_b64 = (samples[0].get('audioBase64') or '').split(',', 1)[-1]
            probe_bytes = base64.b64decode(probe_b64)
            is_webm = len(probe_bytes) >= 4 and probe_bytes[:4] == b"\x1A\x45\xDF\xA3"
        except Exception:
            is_webm = False

    # Log de formato detectado
    if uses_spectrogram:
        print("Formato detectado: samples[].spectrogram (pronto para treino)")
    elif uses_audio_b64:
        if is_webm:
            print(f"Formato detectado: samples[].audioBase64 = WebM/Opus (MediaRecorder) | ffmpeg disponível: {'sim' if _FFMPEG_AVAILABLE else 'não'}")
        else:
            print("Formato detectado: samples[].audioBase64 = WAV/PCM")
    else:
        print("Formato detectado: desconhecido")

    # Pré-checagem: usa WebM e ffmpeg ausente
    if uses_audio_b64 and is_webm and not _FFMPEG_AVAILABLE:
        raise SystemExit(
            "Dataset usa audioBase64 em WebM/Opus e o ffmpeg não está no PATH.\n"
            "Opções: instale o ffmpeg e rode novamente, ou reexporte pelo navegador "
            "em formato de espectrogramas (kws-samples.json com samples[].spectrogram)."
        )

    X_list = []
    y_labels = []

    decoded = 0
    total = len(samples)

    if uses_spectrogram:
        # Espera espectrogramas 2D por amostra
        for s in samples:
            spec = np.array(s['spectrogram'], dtype=np.float32)
            X_list.append(spec)
            y_labels.append(s['label'])
            decoded += 1
    elif uses_audio_b64:
        # Converte áudio base64 -> MFCC 13xT com parâmetros compatíveis ao runtime
        for idx, s in enumerate(samples):
            mfcc = _decode_wav_base64_to_mfcc(s.get('audioBase64', ''))
            if mfcc is None:
                continue
            X_list.append(mfcc.astype(np.float32))
            y_labels.append(s['label'])
            decoded += 1
        if not X_list:
            raise ValueError("Falha ao decodificar qualquer amostra de áudio base64.")
        # Uniformiza T (tempo) para o máximo/min comum se necessário
        # Como recortamos/pad no decode, shapes devem estar consistentes.
        # Ainda assim, garantimos mesma largura usando o comprimento do primeiro.
        target_w = X_list[0].shape[1]
        X_list = [x[:, :target_w] if x.shape[1] >= target_w else np.pad(x, ((0,0),(0, target_w - x.shape[1])), mode='constant') for x in X_list]
    else:
        raise ValueError("Formato de samples não reconhecido: esperava 'spectrogram' ou 'audioBase64'.")

    X = np.stack(X_list, axis=0)
    print(f"Shape X: {X.shape}")
    print(f"Amostras decodificadas: {decoded}/{total}")

    label_to_int = {label: i for i, label in enumerate(labels)}
    y = np.array([label_to_int[lbl] for lbl in y_labels], dtype=np.int64)

    # Salva mapeamento int->label
    int_to_label = {i: label for i, label in enumerate(labels)}
    if not os.path.exists(OUTPUT_MODEL_DIR):
        os.makedirs(OUTPUT_MODEL_DIR)
    labels_path = os.path.join(OUTPUT_MODEL_DIR, OUTPUT_LABELS_NAME)
    with open(labels_path, 'w', encoding='utf-8') as f:
        json.dump(int_to_label, f, ensure_ascii=False)
    print(f"Labels salvos em {labels_path}")

    return X, y, labels

def build_model(input_shape, num_classes):
    model = Sequential([
        Reshape(input_shape + (1,), input_shape=input_shape),
        
        Conv2D(8, (2, 2), activation='relu'),
        MaxPooling2D((2, 2), strides=(2, 2)),
        
        Conv2D(16, (2, 2), activation='relu'),
        MaxPooling2D((2, 2), strides=(2, 2)),

        Flatten(),
        Dropout(0.25),
        Dense(64, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax')
    ])
    
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

def main():
    print("--- Treinamento do Modelo de Key-Word Spotting (KWS) ---")
    
    if not os.path.exists(INPUT_JSON_PATH):
        print(f"ERRO: Arquivo de dados '{INPUT_JSON_PATH}' não encontrado.")
        print("Por favor, colete as amostras de voz na interface web e exporte o arquivo 'kws-samples.json' para a raiz do projeto.")
        return

    X, y, labels = load_data_from_json(INPUT_JSON_PATH)
    if len(X) == 0:
        print("Nenhum dado encontrado no arquivo JSON.")
        return
        
    num_classes = len(labels)
    y_cat = to_categorical(y, num_classes=num_classes)
    
    print("\n2. Dividindo os dados...")
    X_train, X_test, y_train, y_test = train_test_split(X, y_cat, test_size=TEST_SIZE, stratify=y, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=VALIDATION_SIZE, stratify=y_train, random_state=42)

    print(f"  - Dados de treino: {X_train.shape[0]} amostras")
    print(f"  - Dados de validação: {X_val.shape[0]} amostras")
    print(f"  - Dados de teste: {X_test.shape[0]} amostras")

    print("\n3. Construindo o modelo de rede neural...")
    input_shape = X_train.shape[1:]
    model = build_model(input_shape, num_classes)
    model.summary()

    print("\n4. Iniciando o treinamento...")
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=0.0001)
    ]
    
    history = model.fit(
        X_train, y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(X_val, y_val),
        callbacks=callbacks
    )

    print("\n5. Avaliando o modelo com os dados de teste...")
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"  - Acurácia no teste: {test_acc:.2f}")
    print(f"  - Perda no teste: {test_loss:.4f}")

    print("\n6. Salvando o modelo treinado (.h5)...")
    model_path = os.path.join(OUTPUT_MODEL_DIR, OUTPUT_MODEL_NAME)
    model.save(model_path)
    print(f"Modelo salvo em: {model_path}")

    print("\n7. Convertendo modelo para formato TensorFlow.js...")
    try:
        output_web_dir = os.path.join(os.path.dirname(OUTPUT_MODEL_DIR), 'kws_web')
        if not os.path.exists(output_web_dir):
            os.makedirs(output_web_dir)
        
        labels_path = os.path.join(OUTPUT_MODEL_DIR, OUTPUT_LABELS_NAME)
        shutil.copy(labels_path, output_web_dir)

        command = f'tensorflowjs_converter --input_format=keras {model_path} {output_web_dir}'
        print(f"Executando: {command}")
        result = os.system(command)
        if result == 0:
            print(f"Modelo convertido com sucesso para: {output_web_dir}")
        else:
            raise Exception(f"O comando tensorflowjs_converter falhou com código de saída {result}.")
    except Exception as e:
        print(f"ERRO durante a conversão para TensorFlow.js: {e}")
        print("  - Verifique se o `tensorflowjs` está instalado corretamente (`pip install tensorflowjs`).")
    
    print("\n--- Treinamento concluído! ---")

if __name__ == '__main__':
    main()
