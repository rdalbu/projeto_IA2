
window.KwsCollector = (() => {
  let kwsData = {
    classes: [],
    samples: [],
    config: {
      sampleRate: 16000,
      durationSeconds: 1,
    },
  };

  let audioContext = null;
  let mediaStreamSource = null;
  let processor = null;

  function setClasses(labels) {
    if (!Array.isArray(labels) || labels.some(l => typeof l !== 'string')) {
      throw new Error('Labels devem ser um array de strings.');
    }
    kwsData.classes = labels;
    kwsData.samples = kwsData.samples.filter(s => kwsData.classes.includes(s.label));
  }

  function getCounts() {
    const counts = kwsData.classes.map(label => ({
      label,
      count: kwsData.samples.filter(s => s.label === label).length,
    }));
    return counts;
  }

  function clearSamplesForClass(label) {
    kwsData.samples = kwsData.samples.filter(s => s.label !== label);
  }

  function addSample(label, audioBlob) {
    if (!kwsData.classes.includes(label)) {
      throw new Error(`Classe '${label}' não definida.`);
    }
    const reader = new FileReader();
    reader.readAsDataURL(audioBlob);
    reader.onloadend = () => {
      const base64Audio = reader.result;
      kwsData.samples.push({ label, audioBase64: base64Audio });
      console.log(`Amostra de áudio adicionada para a classe '${label}'`);
    };
  }

  function downloadDataset() {
    if (kwsData.samples.length === 0) {
      alert("Nenhuma amostra de áudio foi gravada ainda.");
      return;
    }
    const jsonStr = JSON.stringify(kwsData, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'kws-dataset.json';
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

  async function startRecording(onSampleReady) {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: kwsData.config.sampleRate });
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaStreamSource = audioContext.createMediaStreamSource(stream);
    
    const recorder = new MediaRecorder(stream);
    const chunks = [];
    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'audio/wav' });
      onSampleReady(blob);
      stream.getTracks().forEach(track => track.stop());
    };

    recorder.start();
    setTimeout(() => recorder.stop(), kwsData.config.durationSeconds * 1000);
  }

  return {
    setClasses,
    getCounts,
    clearSamplesForClass,
    addSample,
    downloadDataset,
    loadDataset,
    startRecording,
  };
})();
