
import tensorflow as tf
import numpy as np
import librosa
import json
import os

class KwsClassifier:
    def __init__(self, model_path, labels_path, sample_rate=16000, duration=1, n_mfcc=13):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo KWS não encontrado em: {model_path}")
        if not os.path.exists(labels_path):
            raise FileNotFoundError(f"Arquivo de labels KWS não encontrado em: {labels_path}")

        self.model = tf.keras.models.load_model(model_path)
        
        with open(labels_path, 'r') as f:
            self.int_to_label = json.load(f)
        
        self.sample_rate = sample_rate
        self.duration = duration
        self.n_mfcc = n_mfcc
        self.expected_length = int(self.sample_rate * self.duration)

    def preprocess(self, audio_data):
        if len(audio_data) < self.expected_length:
            audio_data = np.pad(audio_data, (0, self.expected_length - len(audio_data)), 'constant')
        else:
            audio_data = audio_data[:self.expected_length]
        
        # Extrai MFCCs
        mfcc = librosa.feature.mfcc(y=audio_data, sr=self.sample_rate, n_mfcc=self.n_mfcc)
        
        # Adiciona uma dimensão de batch
        mfcc = np.expand_dims(mfcc, axis=0)
        return mfcc

    def predict(self, audio_data):
        """Faz uma predição em um trecho de áudio."""
        mfcc = self.preprocess(audio_data)
        
        # Faz a predição
        prediction = self.model.predict(mfcc, verbose=0)
        
        # Obtém o label e a probabilidade
        predicted_index = np.argmax(prediction)
        probability = np.max(prediction)
        
        label = self.int_to_label.get(str(predicted_index), "desconhecido")
        
        return label, probability
