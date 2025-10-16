import json
import numpy as np
import tensorflow as tf
import os

DATASET_PATH = 'gesture-dataset.json'
OUTPUT_MODEL_DIR = 'models/meu_modelo'
OUTPUT_MODEL_NAME = 'hand-gesture.h5'

print(f"Carregando dataset de '{DATASET_PATH}'...")
try:
    with open(DATASET_PATH, 'r') as f:
        dataset = json.load(f)
except FileNotFoundError:
    print(f"Erro: Arquivo '{DATASET_PATH}' não encontrado.")
    print("Por favor, mova o arquivo que você exportou para a pasta principal do projeto.")
    exit()

features = np.array(dataset['features'])
targets = np.array(dataset['targets'])
labels = dataset['labels']
num_classes = len(labels)
input_dim = features.shape[1]

print(f"Dataset carregado: {len(features)} amostras, {num_classes} classes ({labels}), {input_dim} dimensões.")

print("Construindo o modelo Keras...")
model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(input_dim,)),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(64, activation='relu'),
    tf.keras.layers.Dropout(0.1),
    tf.keras.layers.Dense(num_classes, activation='softmax')
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)
model.summary()

print("\nIniciando o treinamento...")
history = model.fit(
    features,
    targets,
    epochs=30,
    batch_size=32,
    validation_split=0.15,
    shuffle=True
)
print("Treinamento concluído.")

if not os.path.exists(OUTPUT_MODEL_DIR):
    os.makedirs(OUTPUT_MODEL_DIR)
output_path = os.path.join(OUTPUT_MODEL_DIR, OUTPUT_MODEL_NAME)
print(f"Salvando o modelo treinado em '{output_path}'...")
model.save(output_path)
print("Modelo H5 salvo com sucesso!")

print("\nConvertendo modelo para TensorFlow.js...")
os.system(f'tensorflowjs_converter --input_format=keras {output_path} {OUTPUT_MODEL_DIR}')
print(f"Modelo convertido e salvo em '{OUTPUT_MODEL_DIR}'.")
