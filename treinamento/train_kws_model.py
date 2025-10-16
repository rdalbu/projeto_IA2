import os
import numpy as np
import json
import shutil
from sklearn.model_selection import train_test_split
import keras
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, Reshape
from keras.utils import to_categorical
from keras.callbacks import EarlyStopping, ReduceLROnPlateau

# --- Configurações ---
INPUT_JSON_PATH = "kws-samples.json" # Arquivo exportado da UI web
OUTPUT_MODEL_DIR = "models/kws"
OUTPUT_MODEL_NAME = "kws_model.h5"
OUTPUT_LABELS_NAME = "kws_labels.json"

# Parâmetros de treinamento
TEST_SIZE = 0.2
VALIDATION_SIZE = 0.2
BATCH_SIZE = 32
EPOCHS = 50 # Reduzido um pouco pois o treino pode ser mais rápido

def load_data_from_json(json_path):
    """Carrega os dados de espectrograma do arquivo JSON."""
    print(f"Carregando dataset de '{json_path}'...")
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    labels = data['classes']
    samples = data['samples']

    X = np.array([s['spectrogram'] for s in samples])
    y_labels = [s['label'] for s in samples]

    label_to_int = {label: i for i, label in enumerate(labels)}
    y = np.array([label_to_int[lbl] for lbl in y_labels])

    # Salva os labels para a aplicação principal usar
    int_to_label = {i: label for i, label in enumerate(labels)}
    if not os.path.exists(OUTPUT_MODEL_DIR):
        os.makedirs(OUTPUT_MODEL_DIR)
    labels_path = os.path.join(OUTPUT_MODEL_DIR, OUTPUT_LABELS_NAME)
    with open(labels_path, 'w') as f:
        json.dump(int_to_label, f)
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