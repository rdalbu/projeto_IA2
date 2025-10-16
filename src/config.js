window.APP_CONFIG = {
  models: {
    pose: {
      baseURL: "./models/pose/",
      modelURL: "./models/pose/model.json",
      metadataURL: "./models/pose/metadata.json",
    },
  },

  hands: {
    maxNumHands: 2,
    modelComplexity: 1,
    minDetectionConfidence: 0.6,
    minTrackingConfidence: 0.6,
  },
};
