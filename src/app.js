(() => {
  const els = {
    consent: null,
    startBtn: null,
    stopBtn: null,
    status: null,
    video: null,
    overlay: null,
    preds: null,
    useGesture: null,
    gestureClasses: null,
    setClassesBtn: null,
    sampleLabelSelect: null,
    addSampleBtn: null,
    clearClassBtn: null,
    recordBtn: null,
    recordDuration: null,
    trainGestureBtn: null,
    exportDatasetBtn: null,
    importDatasetBtn: null,
    datasetFileInput: null,
    gestureStatus: null,
    gestureCounts: null,
    useKws: null,
    kwsClasses: null,
    setKwsClassesBtn: null,
    kwsSampleLabelSelect: null,
    recordKwsSampleBtn: null,
    kwsRecordDuration: null,
    clearKwsClassBtn: null,
    trainKwsBtn: null,
    importKwsDatasetBtn: null,
    exportKwsDatasetBtn: null,
    kwsDatasetFileInput: null,
    kwsStatus: null,
    kwsCounts: null,
  };

  let mediaStream = null;
  let rafId = null;
  let recognizer = null;

  let poseModel = null;

  let hands = null;
  let lastHands = { hasHands: false, multiHandLandmarks: [], multiHandedness: [] };
  let kwsPreds = [];

  let useGesture = false;
  let useKws = false;
  let recordTimer = null;
  let recordUntil = 0;

  function setStatus(msg, cls = "muted") {
    els.status.className = cls;
    els.status.textContent = msg;
  }

  async function loadTMPose() {
    try {
      const cfg = APP_CONFIG.models.pose;
      poseModel = await tmPose.load(cfg.modelURL, cfg.metadataURL);
    } catch (e) {
      console.warn("Falha ao carregar modelo de pose:", e);
      poseModel = null;
    }
  }

  async function initHands() {
    try {
      const HandsCtor = window.Hands || window.hands || null;
      if (!HandsCtor) throw new Error('Construtor Hands nÃ£o encontrado no escopo global.');
      hands = new HandsCtor({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
      });
      hands.setOptions(APP_CONFIG.hands);
      hands.onResults(onHandsResults);
    } catch (e) {
      console.warn("Falha ao iniciar MediaPipe Hands:", e);
      hands = null;
    }
  }

  async function initRecognizer() {
    if (recognizer) return;
    try {
      recognizer = speechCommands.create('BROWSER_FFT');
      await recognizer.ensureModelLoaded();
    } catch (e) {
      console.error("Falha ao iniciar reconhecedor de voz:", e);
      recognizer = null;
    }
  }

  function onHandsResults(results) {
    const ctx = els.overlay.getContext("2d");
    ctx.clearRect(0, 0, els.overlay.width, els.overlay.height);

    if (results?.multiHandLandmarks?.length) {
      for (const landmarks of results.multiHandLandmarks) {
        window.drawConnectors(ctx, landmarks, window.HAND_CONNECTIONS, { color: '#00FF00', lineWidth: 2 });
        window.drawLandmarks(ctx, landmarks, { color: '#FF0000', lineWidth: 1 });
      }
      lastHands = {
        hasHands: true,
        multiHandLandmarks: results.multiHandLandmarks,
        multiHandedness: results.multiHandedness,
      };
    } else {
      lastHands = { hasHands: false, multiHandLandmarks: [], multiHandedness: [] };
    }
  }

  async function startMedia() {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: true });
    const videoStream = new MediaStream(mediaStream.getVideoTracks());
    els.video.srcObject = videoStream;
    await els.video.play();
    els.overlay.width = els.video.videoWidth || 640;
    els.overlay.height = els.video.videoHeight || 480;
  }

  function stopMedia() {
    if (mediaStream) {
      for (const t of mediaStream.getTracks()) t.stop();
    }
    mediaStream = null;
    els.video.srcObject = null;
  }

  async function predictFrame() {
    if (hands && els.video.readyState >= 2) {
      try {
        await hands.send({ image: els.video });
      } catch (e) {}
    }

    let posePreds = [];
    if (poseModel && els.video.readyState >= 2) {
      try {
        const { pose, posenetOutput } = await poseModel.estimatePose(els.video);
        const preds = await poseModel.predict(posenetOutput);
        posePreds = preds.map(p => ({ className: p.className, probability: p.probability }));
      } catch (e) { } 
    }

    let gesturePreds = [];
    if (useGesture && lastHands.hasHands && lastHands.multiHandLandmarks.length) {
      try {
        const handedness = (lastHands.multiHandedness && lastHands.multiHandedness[0]?.label) || 'Right';
        const feat = window.HandGesture.landmarksToFeatures([ lastHands.multiHandLandmarks[0] ], handedness, { includeZ: false, mirrorX: true });
        if (feat && window.HandGesture.predictProbs) {
          gesturePreds = await window.HandGesture.predictProbs(feat);
        }
      } catch {}
    }

    renderPredictions({ posePreds, gesturePreds, kwsPreds });

    rafId = requestAnimationFrame(predictFrame);
  }

  function renderPredictions({ posePreds, gesturePreds, kwsPreds }) {
    function fmtTop(arr) {
      if (!arr?.length) return "-";
      const top = arr.slice().sort((a,b)=>b.probability-a.probability)[0];
      return `${top.className} (${(top.probability*100).toFixed(1)}%)`;
    }
    const lines = [];
    lines.push(`Pose (Teachable Machine): ${fmtTop(posePreds)}`);
    lines.push(`Gesto (Teste RÃ¡pido):   ${fmtTop(gesturePreds)}`);
    lines.push(`Voz (KWS Teste):        ${fmtTop(kwsPreds)}`);
    lines.push(`MÃ£os (MediaPipe):       ${lastHands.hasHands ? 'detectadas' : 'nÃ£o detectadas'}`);
    
    els.preds.textContent = lines.join("\n");
    els.preds.className = "ok";
  }

  function populateGestureClassSelect() {
    if (!els.sampleLabelSelect) return;
    const currentValue = els.sampleLabelSelect.value;
    const items = window.HandGesture.getCounts();
    els.sampleLabelSelect.innerHTML = '';
    for (const it of items) {
      const opt = document.createElement('option');
      opt.value = it.label;
      opt.textContent = `${it.label} (${it.count})`;
      els.sampleLabelSelect.appendChild(opt);
    }
    if (currentValue) {
      els.sampleLabelSelect.value = currentValue;
    }
  }

  function renderGestureCounts() {
    const items = window.HandGesture.getCounts();
    if (!items.length) { els.gestureCounts.textContent = 'Sem classes.'; return; }
    els.gestureCounts.textContent = items.map(it => `${it.label}: ${it.count}`).join(' | ');
    populateGestureClassSelect();
    updateTrainButtonState();
  }

  function updateTrainButtonState() {
    if (!els.trainGestureBtn) return;
    const items = window.HandGesture.getCounts();
    const nonZero = items.filter(it => (it.count || 0) > 0);
    const ok = items.length >= 2 && nonZero.length >= 2;
    els.trainGestureBtn.disabled = !ok;
  }

  function addCurrentSampleTo(label) {
    if (!label) { els.gestureStatus.textContent = 'Selecione uma classe.'; return false; }
    if (!lastHands.hasHands || !lastHands.multiHandLandmarks.length) { els.gestureStatus.textContent = 'Nenhuma mÃ£o detectada.'; return false; }
    try {
      const handedness = (lastHands.multiHandedness && lastHands.multiHandedness[0]?.label) || 'Right';
      const feat = window.HandGesture.landmarksToFeatures([ lastHands.multiHandLandmarks[0] ], handedness, { includeZ: false, mirrorX: true });
      if (!feat) { els.gestureStatus.textContent = 'Falha ao extrair landmarks.'; return false; }
      window.HandGesture.addSample(label, feat);
      renderGestureCounts();
      return true;
    } catch (e) {
      els.gestureStatus.textContent = `Erro: ${e.message}`;
      return false;
    }
  }

  function startRecording(label, durationMs = 5000, intervalMs = 200) {
    if (recordTimer) return;
    recordUntil = Date.now() + durationMs;
    els.recordBtn.textContent = 'Parar';
    els.recordBtn.disabled = false;

    const tick = () => {
      const remainingMs = recordUntil - Date.now();
      if (remainingMs <= 0) {
        stopRecording();
        return;
      }

      const remainingSec = Math.ceil(remainingMs / 1000);
      els.gestureStatus.textContent = `Gravando... ${remainingSec}s restantes`;

      if (lastHands.hasHands) addCurrentSampleTo(label);
      recordTimer = setTimeout(tick, intervalMs);
    };
    tick();
  }

  function stopRecording() {
    if (recordTimer) clearTimeout(recordTimer);
    recordTimer = null;
    els.recordBtn.textContent = 'Gravar';
    els.gestureStatus.textContent = 'GravaÃ§Ã£o concluÃ­da.';
    updateTrainButtonState();
  }

  function populateKwsClassSelect() {
    if (!els.kwsSampleLabelSelect) return;
    const currentValue = els.kwsSampleLabelSelect.value;
    const items = window.KwsTrainer.getCounts();
    els.kwsSampleLabelSelect.innerHTML = '';
    for (const it of items) {
      const opt = document.createElement('option');
      opt.value = it.label;
      opt.textContent = `${it.label} (${it.count})`;
      els.kwsSampleLabelSelect.appendChild(opt);
    }
    if (currentValue) {
      els.kwsSampleLabelSelect.value = currentValue;
    }
  }

  function renderKwsCounts() {
    const items = window.KwsTrainer.getCounts();
    if (!items.length) { els.kwsCounts.textContent = 'Sem palavras.'; return; }
    els.kwsCounts.textContent = items.map(it => `${it.label}: ${it.count}`).join(' | ');
    populateKwsClassSelect();
    updateKwsTrainButtonState();
  }

  function updateKwsTrainButtonState() {
    if (!els.trainKwsBtn) return;
    const items = window.KwsTrainer.getCounts();
    const nonZero = items.filter(it => (it.count || 0) > 0);
    const ok = items.length >= 2 && nonZero.length >= 2;
    els.trainKwsBtn.disabled = !ok;
  }

  async function startKwsTestListening() {
    if (!recognizer || recognizer.isListening()) return;
    els.kwsStatus.textContent = 'Ouvindo para teste.';
    try {
      await recognizer.listen(async (result) => {
        if (result.spectrogram) {
          const spec = result.spectrogram; const frameSize = Number(spec.frameSize) || (recognizer.params && recognizer.params().numFeatureBins) || null; const total = (spec.data && spec.data.length) || 0; const frames = frameSize ? Math.max(1, Math.floor(total / frameSize)) : null; const feed = (frameSize && frames) ? { data: spec.data, shape: [frameSize, frames] } : spec.data; const preds = await window.KwsTrainer.predictProbs(feed);
          if (preds) kwsPreds = preds;
        }
      }, { includeSpectrogram: true, probabilityThreshold: 0.75, overlapFactor: 0.5 });
    } catch (e) {
      console.error("Erro ao iniciar a escuta de teste KWS:", e);
    }
  }

  async function stopKwsTestListening() {
    if (recognizer && recognizer.isListening()) {
      try {
        await recognizer.stopListening();
      } catch (e) {
        console.warn("Erro ao parar escuta de teste KWS:", e);
      }
    }
    kwsPreds = [];
  }

  async function startAll() {
    try {
      setStatus("Carregando modelosâ€¦", "muted");
      await Promise.all([
        loadTMPose(),
        initHands(),
        initRecognizer(),
      ]);
      setStatus("Inicializando mÃ­diaâ€¦", "muted");
      await startMedia();
      setStatus("Rodando", "ok");
      els.startBtn.disabled = true;
      els.stopBtn.disabled = false;
      rafId = requestAnimationFrame(predictFrame);
    } catch (e) {
      console.error(e);
      setStatus("Erro ao iniciar. Verifique permissÃµes/modelos.", "err");
      await stopAll();
    }
  }

  async function stopAll() {
    cancelAnimationFrame(rafId);
    rafId = null;
    await stopKwsTestListening();
    stopMedia();
    setStatus("Parado.", "muted");
    els.startBtn.disabled = !els.consent.checked;
    els.stopBtn.disabled = true;
  }

  function initUI() {
    els.consent = document.getElementById("consent");
    els.startBtn = document.getElementById("startBtn");
    els.stopBtn = document.getElementById("stopBtn");
    els.status = document.getElementById("status");
    els.video = document.getElementById("video");
    els.overlay = document.getElementById("overlay");
    els.preds = document.getElementById("predictions");

    els.consent.addEventListener("change", () => {
      els.startBtn.disabled = !els.consent.checked;
      setStatus(els.consent.checked ? "Pronto para iniciar." : "Aguardando autorizaÃ§Ã£oâ€¦", "muted");
    });
    els.startBtn.addEventListener("click", startAll);
    els.stopBtn.addEventListener("click", stopAll);

    els.useGesture = document.getElementById("useGesture");
    els.gestureClasses = document.getElementById("gestureClasses");
    els.setClassesBtn = document.getElementById("setClassesBtn");
    els.sampleLabelSelect = document.getElementById("sampleLabelSelect");
    els.addSampleBtn = document.getElementById("addSampleBtn");
    els.clearClassBtn = document.getElementById("clearClassBtn");
    els.recordBtn = document.getElementById("recordBtn");
    els.recordDuration = document.getElementById("recordDuration");
    els.trainGestureBtn = document.getElementById("trainGestureBtn");
    els.exportDatasetBtn = document.getElementById("exportDatasetBtn");
    els.importDatasetBtn = document.getElementById("importDatasetBtn");
    els.datasetFileInput = document.getElementById("datasetFileInput");
    els.gestureStatus = document.getElementById("gestureStatus");
    els.gestureCounts = document.getElementById("gestureCounts");

    els.useGesture.addEventListener('change', () => { useGesture = !!els.useGesture.checked; });

    els.setClassesBtn.addEventListener('click', () => {
      const raw = (els.gestureClasses.value || '').trim();
      if (!raw) return;
      const labels = raw.split(',').map(s => s.trim()).filter(Boolean);
      try {
        window.HandGesture.setClasses(labels);
        els.gestureStatus.textContent = `Classes definidas: ${labels.join(', ')}`;
        renderGestureCounts();
      } catch (e) {
        els.gestureStatus.textContent = `Erro: ${e.message}`;
      }
    });

    els.addSampleBtn.addEventListener('click', () => {
      const label = (els.sampleLabelSelect?.value || '').trim();
      const ok = addCurrentSampleTo(label);
      if (ok) els.gestureStatus.textContent = 'Amostra adicionada.';
    });

    els.clearClassBtn.addEventListener('click', () => {
      const label = (els.sampleLabelSelect?.value || '').trim();
      if (!label) { els.gestureStatus.textContent = 'Selecione uma classe para limpar.'; return; }
      if (confirm(`Tem certeza que deseja apagar todas as amostras da classe "${label}"?`)) {
        try {
          window.HandGesture.clearSamplesForClass(label);
          renderGestureCounts();
          els.gestureStatus.textContent = `Amostras da classe "${label}" foram apagadas.`;
        } catch (e) {
          els.gestureStatus.textContent = `Erro ao limpar: ${e.message}`;
        }
      }
    });

    els.recordBtn.addEventListener('click', () => {
      if (recordTimer) { stopRecording(); return; }
      const label = (els.sampleLabelSelect?.value || '').trim();
      if (!label) { els.gestureStatus.textContent = 'Selecione a classe no seletor.'; return; }
      const durationSec = parseInt(els.recordDuration.value, 10) || 5;
      startRecording(label, durationSec * 1000, 200);
    });

    els.trainGestureBtn.addEventListener('click', async () => {
      try {
        els.gestureStatus.textContent = 'Treinandoâ€¦';
        const hist = await window.HandGesture.train(30, 32);
        const acc = (hist?.val_accuracy?.slice(-1)[0] ?? hist?.accuracy?.slice(-1)[0] ?? 0) * 100;
        els.gestureStatus.textContent = `Treino concluÃ­do. accâ‰ˆ${acc.toFixed(1)}%`;
      } catch (e) {
        els.gestureStatus.textContent = `Erro no treino: ${e.message}`;
      }
    });

    els.exportDatasetBtn.addEventListener('click', () => {
      try {
        window.HandGesture.downloadDataset();
        els.gestureStatus.textContent = 'Dataset exportado como gesture-dataset.json';
      } catch (e) {
        els.gestureStatus.textContent = `Erro ao exportar: ${e.message}`;
      }
    });

    els.importDatasetBtn.addEventListener('click', () => els.datasetFileInput.click());
    els.datasetFileInput.addEventListener('change', async (ev) => {
      try {
        const file = ev.target.files[0];
        if (!file) return;
        const dataset = JSON.parse(await file.text());
        window.HandGesture.loadDataset(dataset);
        renderGestureCounts();
        els.gestureStatus.textContent = `Dataset '${file.name}' carregado.`;
        ev.target.value = '';
      } catch (e) {
        els.gestureStatus.textContent = `Erro ao importar: ${e.message}`;
      }
    });

    els.useKws = document.getElementById("useKws");
    els.kwsClasses = document.getElementById("kwsClasses");
    els.setKwsClassesBtn = document.getElementById("setKwsClassesBtn");
    els.kwsSampleLabelSelect = document.getElementById("kwsSampleLabelSelect");
    els.kwsRecordDuration = document.getElementById("kwsRecordDuration");
    els.recordKwsSampleBtn = document.getElementById("recordKwsSampleBtn");
    els.clearKwsClassBtn = document.getElementById("clearKwsClassBtn");
    els.trainKwsBtn = document.getElementById("trainKwsBtn");
    els.kwsStatus = document.getElementById("kwsStatus");
    els.kwsCounts = document.getElementById("kwsCounts");
    els.importKwsDatasetBtn = document.getElementById("importKwsDatasetBtn");
    els.exportKwsDatasetBtn = document.getElementById("exportKwsDatasetBtn");
    els.kwsDatasetFileInput = document.getElementById("kwsDatasetFileInput");

    els.useKws.addEventListener('change', async (ev) => {
      useKws = !!ev.target.checked;
      if (useKws) {
        await startKwsTestListening();
      } else {
        await stopKwsTestListening();
      }
    });

    els.setKwsClassesBtn.addEventListener('click', () => {
      const raw = (els.kwsClasses.value || '').trim();
      if (!raw) return;
      const labels = raw.split(',').map(s => s.trim()).filter(Boolean);
      try {
        window.KwsTrainer.setClasses(labels);
        els.kwsStatus.textContent = `Palavras definidas: ${labels.join(', ')}`;
        renderKwsCounts();
      } catch (e) {
        els.kwsStatus.textContent = `Erro: ${e.message}`;
      }
    });

    els.recordKwsSampleBtn.addEventListener('click', async () => {
      const label = (els.kwsSampleLabelSelect?.value || '').trim();
      if (!label) { els.kwsStatus.textContent = 'Selecione uma palavra para gravar.'; return; }
      if (!recognizer) { els.kwsStatus.textContent = 'Inicie a captura primeiro.'; return; }
      if (recognizer.isListening()) { els.kwsStatus.textContent = 'Aguarde, reconhecedor ocupado.'; return; }

      const secs = Math.max(1, Math.min(60, parseInt(els.kwsRecordDuration?.value || '1', 10)));
      let added = 0;
      let stopped = false;

      els.recordKwsSampleBtn.disabled = true;
      els.kwsStatus.textContent = `Gravando "${label}" por 1s...`;
      // sobrescreve mensagem com duraÃ§Ã£o escolhida
      els.kwsStatus.textContent = `Gravando "${label}" por ${secs}s...`;

      try {
        await recognizer.listen(result => {
          // recognizer.stopListening(); // adiado para o timer externo
          window.KwsTrainer.addSample(label, result.spectrogram.data);
          // renderKwsCounts(); // adiado para o tÃ©rmino da gravaÃ§Ã£o
          els.kwsStatus.textContent = `Amostra para "${label}" gravada.`;
          // els.recordKwsSampleBtn.disabled = false;
        }, { includeSpectrogram: true, overlapFactor: 0 });
      } catch (e) {
        els.kwsStatus.textContent = `Erro ao gravar: ${e.message}`;
        els.recordKwsSampleBtn.disabled = false;
      }
      setTimeout(async () => {
        try { await recognizer.stopListening(); } catch {}
        renderKwsCounts();
        els.kwsStatus.textContent = `GravaÃ§Ã£o concluÃ­da. Amostras adicionadas: ${added}.`;
        els.recordKwsSampleBtn.disabled = false;
      }, secs * 1000);
    });

    els.clearKwsClassBtn.addEventListener('click', () => {
      const label = (els.kwsSampleLabelSelect?.value || '').trim();
      if (!label) { els.kwsStatus.textContent = 'Selecione uma palavra para limpar.'; return; }
      if (confirm(`Tem certeza que deseja apagar todas as amostras da palavra "${label}"?`)) {
        window.KwsTrainer.clearSamplesForClass(label);
        renderKwsCounts();
        els.kwsStatus.textContent = `Amostras da palavra "${label}" foram apagadas.`;
      }
    });

    els.trainKwsBtn.addEventListener('click', async () => {
      if (!recognizer) { els.kwsStatus.textContent = 'Inicie a captura primeiro.'; return; }
      try {
        els.kwsStatus.textContent = 'Treinando modelo de voz.';
        let frames, bins; try { const p = recognizer.params && recognizer.params(); frames = p && p.numFrames; bins = p && p.numFeatureBins; } catch {} const inputShape = (Number.isFinite(frames) && Number.isFinite(bins)) ? [frames, bins] : undefined;
        const hist = await window.KwsTrainer.train(inputShape, 30, 16);
        const acc = (hist?.history?.val_acc?.slice(-1)[0] ?? hist?.history?.acc?.slice(-1)[0] ?? 0) * 100;
        els.kwsStatus.textContent = `Treino concluÃ­do. accâ‰ˆ${acc.toFixed(1)}%`;
      } catch (e) {
        els.kwsStatus.textContent = `Erro no treino: ${e.message}`;
        console.error(e);
      }
    });

    els.exportKwsDatasetBtn.addEventListener('click', () => {
      try {
        window.KwsTrainer.downloadDataset();
        els.kwsStatus.textContent = 'Dataset de amostras exportado.';
      } catch (e) {
        els.kwsStatus.textContent = `Erro ao exportar: ${e.message}`;
      }
    });

    els.importKwsDatasetBtn.addEventListener('click', () => els.kwsDatasetFileInput.click());
    els.kwsDatasetFileInput.addEventListener('change', async (ev) => {
      try {
        const file = ev.target.files[0];
        if (!file) return;
        const dataset = JSON.parse(await file.text());
        window.KwsTrainer.loadDataset(dataset);
        renderKwsCounts();
        els.kwsStatus.textContent = `Dataset '${file.name}' carregado.`;
        ev.target.value = '';
      } catch (e) {
        els.kwsStatus.textContent = `Erro ao importar: ${e.message}`;
      }
    });

    renderGestureCounts();
    renderKwsCounts();
  }

  window.addEventListener("DOMContentLoaded", initUI);
})();



