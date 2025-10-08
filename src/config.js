// Configurações da aplicação (ajuste conforme seu projeto)
window.APP_CONFIG = {
  // Caminhos padrão dos modelos exportados do Teachable Machine (TF.js)
  models: {
    pose: {
      baseURL: "./models/pose/",
      modelURL: "./models/pose/model.json",
      metadataURL: "./models/pose/metadata.json",
    },
  },

  // MediaPipe Hands
  hands: {
    maxNumHands: 2,
    modelComplexity: 1,
    minDetectionConfidence: 0.6,
    minTrackingConfidence: 0.6,
  },
};
