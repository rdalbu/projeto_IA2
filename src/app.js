(() => {
  const els = {
    consent: null,
    startBtn: null,
    stopBtn: null,
    status: null,
    video: null,
    overlay: null,
    preds: null,
    // gesture UI
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
  };

  let mediaStream = null;
  let rafId = null;

  let poseModel = null;

  let hands = null;
  let lastHands = { hasHands: false, multiHandLandmarks: [], multiHandedness: [] };

  let useGesture = false;
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
      if (!HandsCtor) throw new Error('Construtor Hands não encontrado no escopo global.');
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
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
    els.video.srcObject = mediaStream;
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

    renderPredictions({ posePreds, gesturePreds });

    rafId = requestAnimationFrame(predictFrame);
  }

  function renderPredictions({ posePreds, gesturePreds }) {
    function fmtTop(arr) {
      if (!arr?.length) return "-";
      const top = arr.slice().sort((a,b)=>b.probability-a.probability)[0];
      return `${top.className} (${(top.probability*100).toFixed(1)}%)`;
    }
    const lines = [];
    lines.push(`Pose (Teachable Machine): ${fmtTop(posePreds)}`);
    lines.push(`Gesto (Teste Rápido):   ${fmtTop(gesturePreds)}`);
    lines.push(`Mãos (MediaPipe):       ${lastHands.hasHands ? 'detectadas' : 'não detectadas'}`);
    
    els.preds.textContent = lines.join("\n");
    els.preds.className = "ok";
  }

  function populateClassSelect() {
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

  function renderCounts() {
    const items = window.HandGesture.getCounts();
    if (!items.length) { els.gestureCounts.textContent = 'Sem classes.'; return; }
    els.gestureCounts.textContent = items.map(it => `${it.label}: ${it.count}`).join(' | ');
    populateClassSelect();
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
    if (!lastHands.hasHands || !lastHands.multiHandLandmarks.length) { els.gestureStatus.textContent = 'Nenhuma mão detectada.'; return false; }
    try {
      const handedness = (lastHands.multiHandedness && lastHands.multiHandedness[0]?.label) || 'Right';
      const feat = window.HandGesture.landmarksToFeatures([ lastHands.multiHandLandmarks[0] ], handedness, { includeZ: false, mirrorX: true });
      if (!feat) { els.gestureStatus.textContent = 'Falha ao extrair landmarks.'; return false; }
      window.HandGesture.addSample(label, feat);
      renderCounts();
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
    els.gestureStatus.textContent = 'Gravação concluída.';
    updateTrainButtonState();
  }

  async function startAll() {
    try {
      setStatus("Carregando modelos…", "muted");
      await Promise.all([
        loadTMPose(),
        initHands(),
      ]);
      setStatus("Inicializando mídia…", "muted");
      await startMedia();
      setStatus("Rodando", "ok");
      els.startBtn.disabled = true;
      els.stopBtn.disabled = false;
      rafId = requestAnimationFrame(predictFrame);
    } catch (e) {
      console.error(e);
      setStatus("Erro ao iniciar. Verifique permissões/modelos.", "err");
      await stopAll();
    }
  }

  async function stopAll() {
    cancelAnimationFrame(rafId);
    rafId = null;
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

    // gesture UI
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

    els.consent.addEventListener("change", () => {
      els.startBtn.disabled = !els.consent.checked;
      setStatus(els.consent.checked ? "Pronto para iniciar." : "Aguardando autorização…", "muted");
    });
    els.startBtn.addEventListener("click", startAll);
    els.stopBtn.addEventListener("click", stopAll);

    els.useGesture.addEventListener('change', () => {
      useGesture = !!els.useGesture.checked;
    });

    els.setClassesBtn.addEventListener('click', () => {
      const raw = (els.gestureClasses.value || '').trim();
      if (!raw) return;
      const labels = raw.split(',').map(s => s.trim()).filter(Boolean);
      try {
        window.HandGesture.setClasses(labels);
        els.gestureStatus.textContent = `Classes definidas: ${labels.join(', ')}`;
        renderCounts();
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
          renderCounts();
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
        els.gestureStatus.textContent = 'Treinando…';
        const hist = await window.HandGesture.train(30, 32);
        const acc = (hist?.val_accuracy?.slice(-1)[0] ?? hist?.accuracy?.slice(-1)[0] ?? 0) * 100;
        els.gestureStatus.textContent = `Treino concluído. acc≈${acc.toFixed(1)}%`;
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
        renderCounts();
        els.gestureStatus.textContent = `Dataset '${file.name}' carregado.`;
        ev.target.value = '';
      } catch (e) {
        els.gestureStatus.textContent = `Erro ao importar: ${e.message}`;
      }
    });

    function renderCounts() {
      const items = window.HandGesture.getCounts();
      if (!items.length) { els.gestureCounts.textContent = 'Sem classes.'; return; }
      els.gestureCounts.textContent = items.map(it => `${it.label}: ${it.count}`).join(' | ');
      populateClassSelect();
      updateTrainButtonState();
    }

    updateTrainButtonState();
  }

  window.addEventListener("DOMContentLoaded", initUI);
})();