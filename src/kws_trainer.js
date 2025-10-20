
window.KwsTrainer = (() => {
  let kwsData = { classes: [], samples: [] };
  let model = null;
  let recognizer = null;

  const SPECTROGRAM_CONFIG = {
    fftSize: 1024,
    sampleRate: 44100,
    hopLength: 441,
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
    kwsData.samples.push({ label, spectrogram: Array.from(spectrogram) });
  }

  function buildModel(inputShape, numClasses) {
    // inputShape esperado [H, W]
    if (!Array.isArray(inputShape) || inputShape.length !== 2) {
      throw new Error(`inputShape inválido: ${JSON.stringify(inputShape)}`);
    }
    const [H, W] = inputShape.map(x => Number(x));
    if (!Number.isFinite(H) || !Number.isFinite(W)) {
      throw new Error(`inputShape com dimensões não numéricas: ${JSON.stringify(inputShape)}`);
    }

    model = tf.sequential();
    model.add(tf.layers.reshape({ inputShape, targetShape: [H, W, 1] }));

    model.add(tf.layers.conv2d({ filters: 8, kernelSize: [2, 2], activation: 'relu', padding: 'same' }));
    model.add(tf.layers.maxPooling2d({ poolSize: [2, 2], strides: [2, 2] }));

    model.add(tf.layers.conv2d({ filters: 16, kernelSize: [2, 2], activation: 'relu', padding: 'same' }));
    model.add(tf.layers.maxPooling2d({ poolSize: [2, 2], strides: [2, 2] }));

    // Evita erro do Flatten com shape parcial (passa config vazio para compatibilidade)
    model.add(tf.layers.globalAveragePooling2d({}));
    model.add(tf.layers.dropout({ rate: 0.25 }));
    model.add(tf.layers.dense({ units: 64, activation: 'relu' }));
    model.add(tf.layers.dropout({ rate: 0.5 }));
    model.add(tf.layers.dense({ units: numClasses, activation: 'softmax' }));

    model.compile({ optimizer: tf.train.adam(), loss: 'categoricalCrossentropy', metrics: ['accuracy'] });
    return model;
  }

  function toSpectrogram2D(spec) {
    // Aceita string JSON, objeto {data, shape}, 2D array ou 1D array
    let val = spec;
    try {
      if (typeof val === 'string') {
        // tentar JSON.parse se vier como texto
        val = JSON.parse(val);
      }
    } catch {}

    // Objeto com shape + data
    if (val && typeof val === 'object' && (Array.isArray(val.data) || ArrayBuffer.isView(val.data)) && Array.isArray(val.shape) && val.shape.length === 2) {
      const H = Number(val.shape[0])|0, W = Number(val.shape[1])|0;
      const data = ArrayBuffer.isView(val.data) ? Array.from(val.data) : val.data;
      if (H > 0 && W > 0 && Array.isArray(data) && data.length >= H*W) {
        const out = new Array(H);
        for (let i=0;i<H;i++) {
          out[i] = data.slice(i*W, (i+1)*W).map(v => Number(v) || 0);
        }
        return out;
      }
    }

    // Objeto com data + frameSize (speech-commands)
    if (val && typeof val === 'object' && (Array.isArray(val.data) || ArrayBuffer.isView(val.data)) && Number.isFinite(Number(val.frameSize))) {
      const frameSize = Number(val.frameSize) | 0;
      const data = ArrayBuffer.isView(val.data) ? Array.from(val.data) : val.data;
      if (frameSize > 0 && data && data.length >= frameSize) {
        const frames = Math.max(1, Math.floor(data.length / frameSize));
        const H = frameSize, W = frames;
        const out = new Array(H);
        for (let i=0;i<H;i++) {
          const row = new Array(W);
          for (let j=0;j<W; j++) {
            row[j] = Number(data[j*frameSize + i]) || 0; // interleave to (H,W)
          }
          out[i] = row;
        }
        return out;
      }
    }

    // Já é 2D [H][W]
    if (Array.isArray(val) && Array.isArray(val[0])) return val;

    // 1D -> tentar reconstruir com base em nMelFrames
    if (!(Array.isArray(val) || ArrayBuffer.isView(val))) throw new Error('Espectrograma inválido: não é array.');
    const flat = ArrayBuffer.isView(val) ? Array.from(val) : val;
    const L = flat.length >>> 0;
    const candH = [SPECTROGRAM_CONFIG?.nMelFrames || 40, 40, 13];
    let H = null, W = null;
    for (const h of candH) {
      if (h > 0 && L % h === 0) { H = h; W = L / h; break; }
    }
    if (!H) { H = candH[0]; W = Math.max(1, Math.floor(L / H)); }
    const out = new Array(H);
    for (let i = 0; i < H; i++) {
      const start = i * W;
      const row = flat.slice(start, start + W);
      // pad se faltar
      while (row.length < W) row.push(0);
      out[i] = row.map(v => Number(v) || 0);
    }
    return out;
  }

  function inferInputShapeFromSamples() {
    if (!Array.isArray(kwsData.samples) || kwsData.samples.length === 0) {
      throw new Error('Sem amostras para inferir o inputShape.');
    }
    // Procura a primeira amostra com espectrograma válido
    for (const s of kwsData.samples) {
      try {
        if (!s || !('spectrogram' in s)) continue;
        const A2 = toSpectrogram2D(s.spectrogram);
        const H = A2.length;
        const W = (Array.isArray(A2[0]) ? A2[0].length : 0);
        if (H && W) return [H, W];
      } catch {}
    }
    throw new Error('Nenhuma amostra com spectrogram 2D válido encontrada no dataset.');
  }

  function padOrCrop2D(arr, H, W) {
    // Normaliza para 2D e ajusta tamanho
    const base = toSpectrogram2D(arr);
    const out = new Array(H);
    for (let i = 0; i < H; i++) {
      const row = (base[i] || []);
      const newRow = new Array(W);
      for (let j = 0; j < W; j++) {
        newRow[j] = Number.isFinite(row[j]) ? row[j] : 0;
      }
      out[i] = newRow;
    }
    return out;
  }

  async function train(inputShape, epochs = 30, batchSize = 16) {
    if (kwsData.samples.length < 2) {
      throw new Error('Amostras insuficientes para treinar.');
    }

    // Inferir shape se não fornecido
    // Validação de formato: o trainer web espera samples[].spectrogram (matriz 2D)
    if (!('spectrogram' in (kwsData.samples[0] || {}))) {
      const hasAudioB64 = 'audioBase64' in (kwsData.samples[0] || {});
      const msg = hasAudioB64
        ? 'Este dataset contém audioBase64 (formato do coletor/gravação bruta). Para treinar no navegador, exporte pelo KWS Trainer (samples[].spectrogram). Alternativa: treine no Python (train_kws_model.py) com ffmpeg instalado.'
        : 'Dataset KWS inválido para o navegador. Esperado samples[].spectrogram (matriz 2D).';
      try {
        const el = document.getElementById('kwsStatus');
        if (el) el.textContent = msg;
      } catch {}
      throw new Error(msg);
    }
    let shape = (Array.isArray(inputShape) && inputShape.length === 2) ? inputShape : null;
    if (!shape) {
      shape = inferInputShapeFromSamples();
    } else {
      const a = Number(shape[0]);
      const b = Number(shape[1]);
      if (!Number.isFinite(a) || !Number.isFinite(b) || a <= 0 || b <= 0) {
        shape = inferInputShapeFromSamples();
      } else {
        shape = [a, b];
      }
    }
    try {
      if (typeof document !== 'undefined') {
        const el = document.getElementById('kwsStatus');
        if (el) {
          // Mostrar contagens por classe e shape
          const counts = kwsData.classes.map(label => ({
            label,
            count: kwsData.samples.filter(s => s.label === label).length,
          }));
          const cstr = counts.map(c => `${c.label}:${c.count}`).join(' | ');
          el.textContent = `KWS: inputShape=[${shape[0]}, ${shape[1]}] | ${cstr}`;
        }
      }
    } catch {}
    console.log('[KWS Trainer] inputShape =', shape);
    // Padronizar todos os espectrogramas para o mesmo [H, W]
    const [H, W] = shape;
    const data2d = [];
    const lbls = [];
    let kept = 0, dropped = 0;
    for (const s of kwsData.samples) {
      try {
        if (!s || !('spectrogram' in s)) { dropped++; continue; }
        const m = padOrCrop2D(s.spectrogram, H, W);
        data2d.push(m);
        lbls.push(kwsData.classes.indexOf(s.label));
        kept++;
      } catch {
        dropped++;
      }
    }
    if (kept < 2) {
      throw new Error(`Amostras válidas insuficientes após normalização. Mantidas=${kept}, Descartadas=${dropped}.`);
    }

    buildModel(shape, kwsData.classes.length);

    const xs = tf.tensor(data2d);
    const ys = tf.oneHot(lbls, kwsData.classes.length);

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
    try {
      const ishape = model.inputs?.[0]?.shape || [];
      // ishape esperado: [null, H, W]
      const H = Number(ishape[1]) || SPECTROGRAM_CONFIG.nMelFrames || 40;
      const W = Number(ishape[2]) || 100;
      const m2d = padOrCrop2D(spectrogram, H, W);
      const inputTensor = tf.tensor([m2d]);
      const prediction = model.predict(inputTensor);
      const probabilities = await prediction.data();
      inputTensor.dispose();
      prediction.dispose();
      return Array.from(probabilities);
    } catch (e) {
      // Silencia falhas ocasionais de frames inválidos durante listen()
      return null;
    }
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
