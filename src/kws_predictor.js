window.KwsPredictor = (() => {
  let recognizer = null;
  let isRunning = false;
  let onPrediction = null;
  let labels = [];

  async function init(options) {
    if (!window.speechCommands) {
      throw new Error('Biblioteca speech-commands.min.js não foi carregada.');
    }
    if (recognizer) {
      await recognizer.stopListening();
      recognizer = null;
    }

    onPrediction = options.onPrediction;

    try {
      recognizer = speechCommands.create(
        'BROWSER_FFT',
        null,
        options.modelURL,
        options.metadataURL
      );

      await recognizer.ensureModelLoaded();

      labels = recognizer.wordLabels();
      console.log(`Preditor KWS inicializado. Labels: ${labels.join(', ')}`);
    } catch (e) {
      console.error('Erro ao inicializar o preditor KWS:', e);
      throw e;
    }
  }

  async function start() {
    if (!recognizer) {
      throw new Error('Preditor KWS não inicializado. Chame init() primeiro.');
    }
    if (isRunning) return;

    try {
      await recognizer.listen(
        (result) => {
          const scores = Array.from(result.scores);
          const preds = scores.map((score, i) => ({
            className: labels[i],
            probability: score,
          }));

          if (onPrediction) {
            onPrediction(preds);
          }
        },
        {
          includeSpectrogram: false,
          probabilityThreshold: 0.7,
          invokeCallbackOnNoiseAndUnknown: true,
          overlapFactor: 0.5,
        }
      );
      isRunning = true;
      console.log('Escuta de KWS iniciada.');
    } catch (e) {
      console.error('Erro ao iniciar a escuta de KWS:', e);
    }
  }

  async function stop() {
    if (recognizer && recognizer.isListening()) {
      try {
        await recognizer.stopListening();
        isRunning = false;
        console.log('Escuta de KWS parada.');
      } catch (e) {
        console.warn('Erro ao parar a escuta de KWS (pode já ter parado):', e);
        isRunning = false;
      }
    }
  }

  function isInitialized() {
    return !!recognizer;
  }

  return {
    init,
    start,
    stop,
    isInitialized,
  };
})();
