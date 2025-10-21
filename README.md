# Controle de Mídia por Gestos e Voz (IA + ESP32)

Controle de mídia (play/pause, próxima, anterior) usando gestos de mão (webcam) e/ou palavras‑chave (microfone). A saída pode ser local (teclas multimídia no PC) ou via ESP32 como teclado Bluetooth (universal para celular/TV).

—

## Visão Geral

Pipeline principal

`Webcam` → `MediaPipe Hands` → `Keras` → `Comandos` → `Serial (ESP32)` ou `Teclas Locais`

Opcional: `Microfone` → `KWS (voz)` → `Comandos`.

Recursos

- Gestos em tempo real (MediaPipe + Keras)
- KWS (voz) opcional, tanto no navegador quanto em Python
- Painel web (FastAPI) com preview, overlay, KWS on/off e modo de saída PC x ESP32
- Front “Teste Rápido” em `index.html` (treina no navegador)
- Treinadores Python (gestos e KWS) para gerar modelos finais

—

## Estrutura

- `index.html` – front de teste rápido (gestos + KWS)
- `src/` – JS do front e utilitários de treino web
- `src/detector_gestos/` – backend (FastAPI, runner, classificadores)
- `treinamento/` – scripts Python de treino (gestos e KWS)
- `esp32_sketch/esp32_controller.ino` – firmware (BLE Keyboard)
- `models/` – saída dos treinadores (Keras/TF.js)
- `tools/run_api.ps1` – sobe API + abre painel

—

## Instalação

Pré‑requisitos

- Windows: Python 3.8+ e PowerShell
- Arduino IDE para o ESP32 (opcional)

Ambiente Python

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

—

## Como Testar

Opção A — Teste Rápido (Front)

1) Servir a pasta (para liberar microfone/câmera):
```
python -m http.server 5500
```
2) Abrir `http://localhost:5500/index.html` e marcar “Autorizo…”.
3) KWS: defina palavras, grave samples, treine e teste em tempo real.
4) Gestos: defina classes, colete frames e treine o modelo de teste.

Opção B — Painel Web (API)

- Script pronto:
```
tools\run_api.ps1
```
Abre `http://127.0.0.1:8000/front`.

- Manual:
```
uvicorn src.detector_gestos.api:app --reload
```

No painel: ligar IA (câmera), ligar KWS (microfone), alternar overlay e saída (PC x ESP32). O preview vem de `/stream` e eventos em tempo real via `WS /ws`.

Opção C — CLI (janela OpenCV)

```
python -m src.detector_gestos.main
```

—

## Treino de Modelos

Gestos (Python)

```
python treinamento\train_model.py
```
Gera modelo Keras e salva em `models/`. Para treinar interativamente via webcam (coleta no ato):

```
python -m src.detector_gestos.train_gesture
```

KWS (Voz)

No navegador (recomendado para teste rápido)

- O front já coleta espectrogramas e treina diretamente.
- Caso importe `kws-dataset.json` com `samples[].audioBase64`, o front agora converte automaticamente para `samples[].spectrogram` antes do treino.

No Python (para modelo final/robusto)

```
python treinamento\train_kws_model.py
```
- Aceita `samples[].spectrogram` diretamente.
- Aceita `samples[].audioBase64` (WebM/Opus) se o `ffmpeg` estiver no PATH (veja `docs/KWS-FFMPEG.md`).
- Salva `models/kws/kws_model.h5` e `models/kws/kws_labels.json`.

—

## ESP32 (Saída Bluetooth)

1) Arduino IDE → abra `esp32_sketch/esp32_controller.ino` e faça upload.
2) Pareie o dispositivo “Controle de Gestos IA” via Bluetooth.
3) No `config.json`, defina `usar_serial: true` e a porta (`COMx`).
4) No painel, selecione “ESP32” em “Saída de Comandos”.

—

## Configuração (`config.json`)

- `usar_serial`: true/false
- `serial_port`: ex. `COM5`, `serial_baudrate`: 115200
- `indice_camera`, `camera_width`, `camera_height`, `camera_fps`
- `usar_modelo_gesto`, `gesto_modelo_path`, `gesto_labels`, `gesto_confianca_minima`, `frames_confirmacao_gesto`
- `usar_kws`, `kws_modelo_path`, `kws_labels_path`, `kws_confianca_minima`, `audio_input_device_index`
- `mapeamento_gestos`, `mapeamento_kws`
- `preview_max_fps`, `jpeg_quality`

Exemplo: `config.json:1`

—

## Datasets e Formatos (KWS)

- `kws-samples.json` com `samples[].spectrogram` → pronto para treino web e Python
- `kws-dataset.json`/`kws-samples.json` com `samples[].audioBase64` → web converte automaticamente; no Python requer `ffmpeg` (WebM/Opus)

Consulte: `docs/KWS-FFMPEG.md:1`.

—

## Solução de Problemas

- “Dataset usa audioBase64 e ffmpeg não está no PATH” → instale o ffmpeg ou use espectrogramas
- “Só prediz ‘pause’ no KWS” → re‑treine após correção de `inputShape`; ideal é coletar e treinar no mesmo frontend (navegador) ou treinar no Python
- “Falha ao abrir câmera” → ver `indice_camera`
- “ESP32 não disponível” → ver `serial_port`; no painel, o modo volta para PC automaticamente

—

## Scripts Úteis

- Painel rápido: `tools/run_api.ps1`
- API manual: `uvicorn src.detector_gestos.api:app --reload`
- Front local: `python -m http.server 5500` → `http://localhost:5500/index.html`
- Treino KWS: `python treinamento\train_kws_model.py`
- Treino Gestos: `python treinamento\train_model.py` ou `python -m src.detector_gestos.train_gesture`

—

## Formatação do Código

- JS/CSS/HTML: Prettier (`.prettierrc.json`)
- Python: Black (`pyproject.toml`). Se quiser aplicar: `pip install black && black .`

—

## Licença e Contribuições

Sinta‑se à vontade para abrir issues e PRs. Melhorias no painel, no pipeline de treino e nas integrações são bem‑vindas.

