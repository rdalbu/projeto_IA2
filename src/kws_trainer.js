
window.KwsTrainer = (() => {
  let kwsData = { classes: [], samples: [] };
  let model = null;
  let recognizer = null; // speech-commands recognizer

  const SPECTROGRAM_CONFIG = {
    fftSize: 1024,
    sampleRate: 44100, // speech-commands works with 44100
    hopLength: 441, // ~10ms
    nMelFrames: 40,
    fmin: 0,
    fmax: 8000,
  };

  function setClasses(labels) {
    if (!Array.isArray(labels) || labels.some(l => typeof l !== 'string')) {
      throw new Error('Labels devem ser um array de strings.');
    }
    kwsData.classes = labels;
    kwsData.samples = kwsData.samples.filter(s => kwsData.classes.includes(s.label));
  }

  function getCounts() {
    return kwsData.classes.map(label => ({
      label,
      count: kwsData.samples.filter(s => s.label === label).length,
    }));
  }

  function clearSamplesForClass(label) {
    kwsData.samples = kwsData.samples.filter(s => s.label !== label);
  }

  function addSample(label, spectrogram) {
    if (!kwsData.classes.includes(label)) {
      throw new Error(`Classe '${label}' não definida.`);
    }
    // A spectrogram from speech-commands is a Float32Array.
    // We need to convert it to a plain array to be stored and cloned.
    kwsData.samples.push({ label, spectrogram: Array.from(spectrogram) });
  }

  function buildModel(inputShape, numClasses) {
    model = tf.sequential();
    model.add(tf.layers.reshape({ inputShape, targetShape: [inputShape[0], inputShape[1], 1] }));
    
    model.add(tf.layers.conv2d({ filters: 8, kernelSize: [2, 2], activation: 'relu' }));
    model.add(tf.layers.maxPooling2d({ poolSize: [2, 2], strides: [2, 2] }));
    
    model.add(tf.layers.conv2d({ filters: 16, kernelSize: [2, 2], activation: 'relu' }));
    model.add(tf.layers.maxPooling2d({ poolSize: [2, 2], strides: [2, 2] }));

    model.add(tf.layers.flatten());
    model.add(tf.layers.dropout({ rate: 0.25 }));
    model.add(tf.layers.dense({ units: 64, activation: 'relu' }));
    model.add(tf.layers.dropout({ rate: 0.5 }));
    model.add(tf.layers.dense({ units: num_classes, activation: 'softmax' }));

    model.compile({
      optimizer: tf.train.adam(),
      loss: 'categoricalCrossentropy',
      metrics: ['accuracy'],
    });
    return model;
  }

  async function train(inputShape, epochs = 30, batchSize = 16) {
    if (kwsData.samples.length < 2) {
      throw new Error('Amostras insuficientes para treinar.');
    }

    // Create and compile the model
    buildModel(inputShape, kwsData.classes.length);

    // Prepare data tensors
    const xs = tf.tensor(kwsData.samples.map(s => s.spectrogram));
    const ys = tf.oneHot(kwsData.samples.map(s => kwsData.classes.indexOf(s.label)), kwsData.classes.length);

    const history = await model.fit(xs, ys, {
      epochs,
      batchSize,
      validationSplit: 0.2,
      callbacks: { onEpochEnd: (epoch, logs) => console.log(`Epoch ${epoch}: loss = ${logs.loss}, acc = ${logs.acc}`) },
    });

    xs.dispose();
    ys.dispose();
    return history;
  }

  async function predict(spectrogram) {
    if (!model) return null;
    const inputTensor = tf.tensor([spectrogram]);
    const prediction = model.predict(inputTensor);
    const probabilities = await prediction.data();
    inputTensor.dispose();
    prediction.dispose();
    return Array.from(probabilities);
  }

  async function predictProbs(spectrogram) {
    const probs = await predict(spectrogram);
    if (!probs) return null;
    return kwsData.classes.map((className, i) => ({ className, probability: probs[i] }));
  }

  async function getRecognizer() {
      if (recognizer && recognizer.isListening()) return recognizer;
      if (recognizer) await recognizer.stopListening();

      recognizer = speechCommands.create('BROWSER_FFT');
      await recognizer.ensureModelLoaded();
      return recognizer;
  }

  function downloadDataset() {
    if (kwsData.samples.length === 0) {
      alert("Nenhuma amostra de voz foi gravada ainda.");
      return;
    }
    const jsonStr = JSON.stringify(kwsData, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'kws-samples.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function loadDataset(dataset) {
    if (!dataset || !dataset.classes || !dataset.samples) {
      throw new Error('Formato de dataset inválido.');
    }
    kwsData = dataset;
  }

  return {
    setClasses,
    getCounts,
    clearSamplesForClass,
    addSample,
    train,
    predictProbs,
    getRecognizer,
    downloadDataset,
    loadDataset,
  };
})();
