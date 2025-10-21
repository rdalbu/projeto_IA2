window.KwsTrainer = (() => {
  let kwsData = { classes: [], samples: [] };
  let model = null;
  let recognizer = null;
  let normParams = null; // { mean: number, std: number }

  const SPECTROGRAM_CONFIG = {
    fftSize: 1024,
    sampleRate: 44100,
    hopLength: 441,
    nMelFrames: 40,
    fmin: 0,
    fmax: 8000,
  };

  async function dataUrlToArrayBuffer(dataUrl) {
    try {
      if (typeof dataUrl !== 'string') return null;
      const parts = dataUrl.split(',', 2);
      const b64 = parts.length === 2 ? parts[1] : parts[0];
      const binary = atob(b64);
      const len = binary.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
      return bytes.buffer;
    } catch {
      return null;
    }
  }

  async function decodeAudioBase64ToPCM(
    audioBase64,
    targetSampleRate = 16000,
    durationSeconds = 1.0
  ) {
    try {
      const arr = await dataUrlToArrayBuffer(audioBase64);
      if (!arr) return null;
      const tmpCtx = new (window.AudioContext || window.webkitAudioContext)();
      const buf = await tmpCtx.decodeAudioData(arr.slice(0));
      let mono;

      if (buf.numberOfChannels > 1) {
        const L = buf.getChannelData(0);
        const R = buf.getChannelData(1);
        const N = Math.min(L.length, R.length);
        mono = new Float32Array(N);
        for (let i = 0; i < N; i++) mono[i] = 0.5 * (L[i] + R[i]);
      } else {
        mono = buf.getChannelData(0).slice();
      }

      let resampled;
      if (buf.sampleRate !== targetSampleRate) {
        const length = Math.max(1, Math.round(buf.duration * targetSampleRate));
        const off = new OfflineAudioContext(1, length, targetSampleRate);
        const src = off.createBufferSource();
        const monoBuf = off.createBuffer(1, buf.length, buf.sampleRate);
        monoBuf.copyToChannel(mono, 0, 0);
        src.buffer = monoBuf;
        src.connect(off.destination);
        src.start();
        const rendered = await off.startRendering();
        resampled = rendered.getChannelData(0).slice();
      } else {
        resampled = mono;
      }

      const targetLen = Math.max(1, Math.round(targetSampleRate * durationSeconds));
      if (resampled.length > targetLen) {
        return resampled.slice(0, targetLen);
      } else if (resampled.length < targetLen) {
        const out = new Float32Array(targetLen);
        out.set(resampled);
        return out;
      }
      return resampled;
    } catch {
      return null;
    }
  }

  async function computeLogSpectrogram2D(pcm, opts = {}) {
    const sr = Number(opts.sampleRate) || 16000;
    const targetBins = Number(opts.targetBins) || SPECTROGRAM_CONFIG?.nMelFrames || 40;
    const targetFrames = Number(opts.targetFrames) || 100;
    const frameLength = Number(opts.frameLength) || 512; // ~32ms @16k
    let hopLength;
    if (Number.isFinite(targetFrames) && targetFrames > 1) {
      hopLength = Math.max(1, Math.floor((pcm.length - frameLength) / (targetFrames - 1)));
    } else {
      hopLength = Number(opts.hopLength) || Math.max(1, Math.floor(frameLength / 2));
    }

    return tf.tidy(() => {
      const x = tf.tensor1d(pcm);
      const frames = tf.signal.frame(x, frameLength, hopLength); // [numFrames, frameLength]
      const win = tf.signal.hannWindow(frameLength);
      const windowed = frames.mul(win);
      const fft = tf.spectral.rfft(windowed); // [numFrames, frameLength/2+1]
      const mags = tf.abs(fft);
      const logm = tf.log1p(mags); // log(1+magnitude)

      const transposed = logm.transpose([1, 0]); // [bins, frames]
      const resized = tf.image
        .resizeBilinear(transposed.expandDims(-1), [targetBins, transposed.shape[1]], true)
        .squeeze(-1);

      const min = resized.min();
      const max = resized.max();
      const norm = resized.sub(min).div(max.sub(min).add(1e-6));
      return norm.arraySync(); // 2D array [H][W]
    });
  }

  async function convertAudioBase64SamplesInPlace(statusEl) {
    let bins = SPECTROGRAM_CONFIG?.nMelFrames || 40;
    let frames = 100;
    try {
      const rec = await getRecognizer();
      const p = rec && rec.params && rec.params();
      if (p && Number.isFinite(p.numFeatureBins)) bins = p.numFeatureBins;
      if (p && Number.isFinite(p.numFrames)) frames = p.numFrames;
    } catch {}

    const total = kwsData.samples.length;
    let done = 0,
      kept = 0,
      failed = 0;
    for (const s of kwsData.samples) {
      done++;
      try {
        if (!s || !s.audioBase64) {
          continue;
        }
        const pcm = await decodeAudioBase64ToPCM(s.audioBase64, 16000, 1.0);
        if (!pcm) {
          failed++;
          continue;
        }
        const spec2d = await computeLogSpectrogram2D(pcm, {
          sampleRate: 16000,
          targetBins: bins,
          targetFrames: frames,
        });
        if (Array.isArray(spec2d) && spec2d.length) {
          s.spectrogram = spec2d; // 2D
          delete s.audioBase64;
          kept++;
        } else {
          failed++;
        }
      } catch {
        failed++;
      }
      try {
        if (statusEl)
          statusEl.textContent = `Convertendo áudio: ${done}/${total} (ok:${kept}, falhas:${failed})`;
      } catch {}
    }
    return { kept, failed, total };
  }

  function setClasses(labels) {
    if (!Array.isArray(labels) || labels.some((l) => typeof l !== 'string')) {
      throw new Error('Labels devem ser um array de strings.');
    }
    kwsData.classes = labels;
    kwsData.samples = kwsData.samples.filter((s) => kwsData.classes.includes(s.label));
  }

  function getCounts() {
    return kwsData.classes.map((label) => ({
      label,
      count: kwsData.samples.filter((s) => s.label === label).length,
    }));
  }

  function clearSamplesForClass(label) {
    kwsData.samples = kwsData.samples.filter((s) => s.label !== label);
  }

  function addSample(label, spectrogram) {
    if (!kwsData.classes.includes(label)) {
      throw new Error(`Classe '${label}' não definida.`);
    }
    kwsData.samples.push({ label, spectrogram: Array.from(spectrogram) });
  }

  function buildModel(inputShape, numClasses) {
    if (!Array.isArray(inputShape) || inputShape.length !== 2) {
      throw new Error(`inputShape inválido: ${JSON.stringify(inputShape)}`);
    }
    const [H, W] = inputShape.map((x) => Number(x));
    if (!Number.isFinite(H) || !Number.isFinite(W)) {
      throw new Error(`inputShape com dimensões não numéricas: ${JSON.stringify(inputShape)}`);
    }

    model = tf.sequential();
    model.add(tf.layers.reshape({ inputShape, targetShape: [H, W, 1] }));

    model.add(
      tf.layers.conv2d({ filters: 8, kernelSize: [2, 2], activation: 'relu', padding: 'same' })
    );
    model.add(tf.layers.maxPooling2d({ poolSize: [2, 2], strides: [2, 2] }));

    model.add(
      tf.layers.conv2d({ filters: 16, kernelSize: [2, 2], activation: 'relu', padding: 'same' })
    );
    model.add(tf.layers.maxPooling2d({ poolSize: [2, 2], strides: [2, 2] }));

    model.add(tf.layers.globalAveragePooling2d({}));
    model.add(tf.layers.dropout({ rate: 0.25 }));
    model.add(tf.layers.dense({ units: 64, activation: 'relu' }));
    model.add(tf.layers.dropout({ rate: 0.5 }));
    model.add(tf.layers.dense({ units: numClasses, activation: 'softmax' }));

    model.compile({
      optimizer: tf.train.adam(),
      loss: 'categoricalCrossentropy',
      metrics: ['accuracy'],
    });
    return model;
  }

  function toSpectrogram2D(spec) {
    let val = spec;
    try {
      if (typeof val === 'string') {
        val = JSON.parse(val);
      }
    } catch {}

    if (
      val &&
      typeof val === 'object' &&
      (Array.isArray(val.data) || ArrayBuffer.isView(val.data)) &&
      Array.isArray(val.shape) &&
      val.shape.length === 2
    ) {
      const H = Number(val.shape[0]) | 0,
        W = Number(val.shape[1]) | 0;
      const data = ArrayBuffer.isView(val.data) ? Array.from(val.data) : val.data;
      if (H > 0 && W > 0 && Array.isArray(data) && data.length >= H * W) {
        const out = new Array(H);
        for (let i = 0; i < H; i++) {
          out[i] = data.slice(i * W, (i + 1) * W).map((v) => Number(v) || 0);
        }
        return out;
      }
    }

    if (
      val &&
      typeof val === 'object' &&
      (Array.isArray(val.data) || ArrayBuffer.isView(val.data)) &&
      Number.isFinite(Number(val.frameSize))
    ) {
      const frameSize = Number(val.frameSize) | 0;
      const data = ArrayBuffer.isView(val.data) ? Array.from(val.data) : val.data;
      if (frameSize > 0 && data && data.length >= frameSize) {
        const frames = Math.max(1, Math.floor(data.length / frameSize));
        const H = frameSize,
          W = frames;
        const out = new Array(H);
        for (let i = 0; i < H; i++) {
          const row = new Array(W);
          for (let j = 0; j < W; j++) {
            row[j] = Number(data[j * frameSize + i]) || 0; // interleave to (H,W)
          }
          out[i] = row;
        }
        return out;
      }
    }

    if (Array.isArray(val) && Array.isArray(val[0])) return val;

    if (!(Array.isArray(val) || ArrayBuffer.isView(val)))
      throw new Error('Espectrograma inválido: não é array.');
    const flat = ArrayBuffer.isView(val) ? Array.from(val) : val;
    const L = flat.length >>> 0;
    const candH = [SPECTROGRAM_CONFIG?.nMelFrames || 40, 40, 13];
    let H = null,
      W = null;
    for (const h of candH) {
      if (h > 0 && L % h === 0) {
        H = h;
        W = L / h;
        break;
      }
    }
    if (!H) {
      H = candH[0];
      W = Math.max(1, Math.floor(L / H));
    }
    const out = new Array(H);
    for (let i = 0; i < H; i++) {
      const start = i * W;
      const row = flat.slice(start, start + W);

      while (row.length < W) row.push(0);
      out[i] = row.map((v) => Number(v) || 0);
    }
    return out;
  }

  function inferInputShapeFromSamples() {
    if (!Array.isArray(kwsData.samples) || kwsData.samples.length === 0) {
      throw new Error('Sem amostras para inferir o inputShape.');
    }

    for (const s of kwsData.samples) {
      try {
        if (!s || !('spectrogram' in s)) continue;
        const A2 = toSpectrogram2D(s.spectrogram);
        const H = A2.length;
        const W = Array.isArray(A2[0]) ? A2[0].length : 0;
        if (H && W) return [H, W];
      } catch {}
    }
    throw new Error('Nenhuma amostra com spectrogram 2D válido encontrada no dataset.');
  }

  function padOrCrop2D(arr, H, W) {
    const base = toSpectrogram2D(arr);
    const out = new Array(H);
    for (let i = 0; i < H; i++) {
      const row = base[i] || [];
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

    if (!('spectrogram' in (kwsData.samples[0] || {}))) {
      const hasAudioB64 = 'audioBase64' in (kwsData.samples[0] || {});
      if (hasAudioB64) {
        let el = null;
        try {
          el = document.getElementById('kwsStatus');
          if (el) el.textContent = 'Convertendo audioBase64 para espectrogramas…';
        } catch {}
        const { kept, failed, total } = await convertAudioBase64SamplesInPlace(el);
        if (!('spectrogram' in (kwsData.samples[0] || {}))) {
          const msgFail = `Falha ao converter dataset (ok:${kept}, falhas:${failed} de ${total}).`;
          if (el) el.textContent = msgFail;
          throw new Error(msgFail);
        }
      } else {
        const msg =
          'Dataset KWS inválido para o navegador. Esperado samples[].spectrogram (matriz 2D).';
        try {
          const el = document.getElementById('kwsStatus');
          if (el) el.textContent = msg;
        } catch {}
        throw new Error(msg);
      }
    }
    let shape = Array.isArray(inputShape) && inputShape.length === 2 ? inputShape : null;
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
          const counts = kwsData.classes.map((label) => ({
            label,
            count: kwsData.samples.filter((s) => s.label === label).length,
          }));
          const cstr = counts.map((c) => `${c.label}:${c.count}`).join(' | ');
          el.textContent = `KWS: inputShape=[${shape[0]}, ${shape[1]}] | ${cstr}`;
        }
      }
    } catch {}
    console.log('[KWS Trainer] inputShape =', shape);

    const [H, W] = shape;
    const data2d = [];
    const lbls = [];
    let kept = 0,
      dropped = 0;
    for (const s of kwsData.samples) {
      try {
        if (!s || !('spectrogram' in s)) {
          dropped++;
          continue;
        }
        const m = padOrCrop2D(s.spectrogram, H, W);
        data2d.push(m);
        lbls.push(kwsData.classes.indexOf(s.label));
        kept++;
      } catch {
        dropped++;
      }
    }
    if (kept < 2) {
      throw new Error(
        `Amostras válidas insuficientes após normalização. Mantidas=${kept}, Descartadas=${dropped}.`
      );
    }

    buildModel(shape, kwsData.classes.length);

    let xs = tf.tensor(data2d);
    const ys = tf.oneHot(lbls, kwsData.classes.length);

    const stats = tf.tidy(() => {
      const meanT = xs.mean();
      const stdT = xs.sub(meanT).square().mean().sqrt().add(1e-6);
      return { mean: meanT.dataSync()[0], std: stdT.dataSync()[0] };
    });
    normParams = { mean: Number(stats.mean) || 0, std: Number(stats.std) || 1 };

    xs = xs.sub(normParams.mean).div(normParams.std);

    const history = await model.fit(xs, ys, {
      epochs,
      batchSize,
      validationSplit: 0.2,
      callbacks: {
        onEpochEnd: (epoch, logs) =>
          console.log(`Epoch ${epoch}: loss = ${logs.loss}, acc = ${logs.acc}`),
      },
    });

    xs.dispose();
    ys.dispose();
    return history;
  }

  async function predict(spectrogram) {
    if (!model) return null;
    try {
      const ishape = model.inputs?.[0]?.shape || [];

      const H = Number(ishape[1]) || SPECTROGRAM_CONFIG.nMelFrames || 40;
      const W = Number(ishape[2]) || 100;
      const m2d = padOrCrop2D(spectrogram, H, W);
      let inputTensor = tf.tensor([m2d]);
      if (normParams && Number.isFinite(normParams.mean) && Number.isFinite(normParams.std)) {
        inputTensor = inputTensor.sub(normParams.mean).div(normParams.std);
      }
      const prediction = model.predict(inputTensor);
      const probabilities = await prediction.data();
      inputTensor.dispose();
      prediction.dispose();
      return Array.from(probabilities);
    } catch (e) {
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
      alert('Nenhuma amostra de voz foi gravada ainda.');
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
