(function () {
  const state = {
    classes: [],
    label2idx: new Map(),
    samplesX: [],
    samplesY: [],
    counts: new Map(),
    model: null,
  };

  function resetDataset() {
    state.samplesX = [];
    state.samplesY = [];
    state.counts = new Map();
  }

  function setClasses(labels) {
    state.classes = labels.slice();
    state.label2idx = new Map(labels.map((l, i) => [l, i]));
    resetDataset();
  }

  function getCounts() {
    return state.classes.map(l => ({ label: l, count: state.counts.get(l) || 0 }));
  }

  // Normalização:
  // - Usa a primeira mão
  // - Centraliza no punho (landmark 0)
  // - Escala pelo maior alcance entre pontos (max distance)
  // - Espelha eixo X para uniformizar left/right se quiser (mirrorX=true)
  function landmarksToFeatures(landmarks, handedness = 'Right', { includeZ = false, mirrorX = true } = {}) {
    if (!Array.isArray(landmarks) || landmarks.length === 0) return null;
    const lm = landmarks[0];
    if (!lm || lm.length < 21) return null;

    const wrist = lm[0];
    const pts = lm.map(p => ({ x: p.x, y: p.y, z: p.z ?? 0 }));

    // Centraliza no punho e espelha se mão esquerda
    const flip = (mirrorX && String(handedness).toLowerCase().startsWith('left')) ? -1 : 1;
    for (const p of pts) {
      p.x = (p.x - wrist.x) * flip;
      p.y = (p.y - wrist.y);
      p.z = (p.z - wrist.z);
    }

    // Escala pelo max range
    let maxRange = 1e-6;
    for (const p of pts) {
      maxRange = Math.max(maxRange, Math.abs(p.x), Math.abs(p.y), Math.abs(p.z));
    }
    for (const p of pts) {
      p.x /= maxRange; p.y /= maxRange; p.z /= maxRange;
    }

    const arr = [];
    for (const p of pts) {
      arr.push(p.x, p.y);
      if (includeZ) arr.push(p.z);
    }
    return new Float32Array(arr);
  }

  function addSample(label, featureVec) {
    if (!state.label2idx.has(label)) throw new Error(`Classe desconhecida: ${label}`);
    state.samplesX.push(featureVec);
    state.samplesY.push(state.label2idx.get(label));
    state.counts.set(label, (state.counts.get(label) || 0) + 1);
  }

  function buildModel(inputDim, numClasses) {
    const model = tf.sequential();
    model.add(tf.layers.dense({ units: 128, activation: 'relu', inputShape: [inputDim] }));
    model.add(tf.layers.dropout({ rate: 0.2 }));
    model.add(tf.layers.dense({ units: 64, activation: 'relu' }));
    model.add(tf.layers.dropout({ rate: 0.1 }));
    model.add(tf.layers.dense({ units: numClasses, activation: 'softmax' }));
    model.compile({ optimizer: tf.train.adam(0.001), loss: 'categoricalCrossentropy', metrics: ['accuracy'] });
    return model;
  }

  async function train(epochs = 30, batchSize = 32) {
    if (!state.samplesX.length) throw new Error('Sem amostras para treinar.');
    if ((state.classes?.length || 0) < 2) throw new Error('Defina ao menos duas classes para treinar.');
    const perClass = state.classes.map(l => ({ label: l, count: state.counts.get(l) || 0 }));
    const withData = perClass.filter(c => c.count > 0);
    if (withData.length < 2) throw new Error('Adicione amostras em pelo menos duas classes.');
    const xs = tf.tensor2d(state.samplesX.map(v => Array.from(v)));
    const ysIdx = tf.tensor1d(state.samplesY, 'int32');
    const ys = tf.oneHot(ysIdx, state.classes.length).toFloat();
    xs.print ? null : null; 
    const model = buildModel(xs.shape[1], state.classes.length);
    const history = await model.fit(xs, ys, {
      epochs, batchSize, shuffle: true, validationSplit: 0.15,
    });
    tf.dispose([xs, ysIdx, ys]);
    state.model = model;
    return history?.history || {};
  }

  async function predictProbs(featureVec) {
    if (!state.model) return [];
    const x = tf.tensor2d([Array.from(featureVec)]);
    const probs = state.model.predict(x);
    const arr = (await probs.data());
    tf.dispose([x, probs]);
    return state.classes.map((label, i) => ({ className: label, probability: arr[i] || 0 }));
  }

  async function saveToIndexedDB(key = 'indexeddb://hand-gesture') {
    if (!state.model) throw new Error('Treine o modelo antes de salvar.');
    await state.model.save(key);
    localStorage.setItem(key + '-labels', JSON.stringify(state.classes));
  }

  async function loadFromIndexedDB(key = 'indexeddb://hand-gesture') {
    state.model = await tf.loadLayersModel(key);

    const labelsJson = localStorage.getItem(key + '-labels');
    if (labelsJson) {
      const labels = JSON.parse(labelsJson);
      setClasses(labels);
    }
    return !!state.model;
  }

  async function loadFromBrowserFiles(fileList) {
    const files = Array.from(fileList || []);
    const modelFile = files.find(f => f.name.endsWith('.json') && f.name !== 'labels.json');
    if (!modelFile) throw new Error('Arquivo model.json não encontrado.');

    // Try to load labels, but don't fail if not present
    const labelsFile = files.find(f => f.name === 'labels.json');
    if (labelsFile) {
        const labels = JSON.parse(await labelsFile.text());
        setClasses(labels);
    } else {
        setClasses([]); 
    }

    state.model = await tf.loadLayersModel(tf.io.browserFiles(files));
    return !!state.model;
  }

  async function downloadModel(name = 'hand-gesture') {
    if (!state.model) throw new Error('Treine o modelo antes de salvar.');

    const labelsJson = JSON.stringify(state.classes);
    const blob = new Blob([labelsJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'labels.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // Then, save the model itself (will trigger another download)
    await state.model.save(`downloads://${name}`);
  }

  async function loadFromUrl(modelUrl) {
    try {
        state.model = await tf.loadLayersModel(modelUrl);
        return !!state.model;
    } catch (e) {
        console.error("Falha ao carregar modelo da URL:", e);
        return false;
    }
  }

  function downloadDataset(name = 'gesture-dataset.json') {
    if (!state.samplesX.length) {
        throw new Error('Nenhum dado de amostra para exportar.');
    }
    const dataset = {
        labels: state.classes,
        features: state.samplesX.map(arr => Array.from(arr)), // Convert Float32Array to plain array
        targets: state.samplesY,
    };
    const json = JSON.stringify(dataset);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function loadDataset(dataset) {
    if (!dataset || !dataset.labels || !dataset.features || !dataset.targets) {
      throw new Error('Arquivo de dataset inválido ou corrompido.');
    }
    setClasses(dataset.labels);
    // Recalcula a contagem a partir dos dados carregados
    state.counts.clear();
    for (const target of dataset.targets) {
      const label = state.classes[target];
      if (label) {
        state.counts.set(label, (state.counts.get(label) || 0) + 1);
      }
    }
    // Carrega as amostras
    state.samplesX = dataset.features.map(f => new Float32Array(f));
    state.samplesY = dataset.targets;
  }

  function clearSamplesForClass(labelToClear) {
    if (!state.label2idx.has(labelToClear)) {
        throw new Error(`Classe desconhecida: ${labelToClear}`);
    }
    const classIdxToClear = state.label2idx.get(labelToClear);

    const newSamplesX = [];
    const newSamplesY = [];

    for (let i = 0; i < state.samplesY.length; i++) {
        if (state.samplesY[i] !== classIdxToClear) {
            newSamplesX.push(state.samplesX[i]);
            newSamplesY.push(state.samplesY[i]);
        }
    }

    state.samplesX = newSamplesX;
    state.samplesY = newSamplesY;
    state.counts.set(labelToClear, 0); // Reset count for the cleared class
  }

  window.HandGesture = {
    setClasses,
    getCounts,
    addSample,
    train,
    predictProbs,
    landmarksToFeatures,
    saveToIndexedDB,
    loadFromIndexedDB,
    loadFromBrowserFiles,
    downloadModel,
    loadFromUrl, 
    downloadDataset, 
    loadDataset, 
    clearSamplesForClass, 
  };
})();
