# AI Gesture & Voice Media Control (ESP32 + Browser/Python)

Control media (play/pause, next, previous) via hand gestures (webcam) and/or voice keywords (microphone). Output can be local (PC media keys) or through an ESP32 acting as a Bluetooth keyboard.

—

## Quick Start

1) Windows + PowerShell (project root):
```
tools\run_api.ps1
```
2) Open `http://127.0.0.1:8000/front` and enable Camera/Mic.
3) Optional: connect ESP32 and switch output to “ESP32”.

—

## Table of Contents

- [Overview](#overview)
- [Requirements](#requirements)
- [Installation](#installation)
- [How to Run](#how-to-run)
- [Training](#training)
- [ESP32](#esp32-output)
- [Configuration](#configuration-configjson)
- [KWS Datasets](#kws-datasets--formats)
- [FAQ / Troubleshooting](#faq--troubleshooting)
- [Privacy](#privacy)
- [Code Style](#code-style)
- [Contributing](#contributing)

—

## Overview

Pipeline

`Webcam` → `MediaPipe Hands` → `Keras` → `Commands` → `Serial (ESP32)` or `Local Keys`

Optional: `Microphone` → `KWS (voice)` → `Commands`.

Features

- Real‑time gestures (MediaPipe + Keras)
- Voice KWS in Browser and Python
- FastAPI Web Panel: preview, overlay toggle, KWS on/off, PC vs ESP32 output
- Quick Test front (`index.html`) with in‑browser training
- Python trainers (gestures + KWS) for final models

—

## Requirements

- Windows 10/11 recommended
- Python 3.10/3.11 (3.8+ works)
- PowerShell
- Arduino IDE (for ESP32)
- ffmpeg (only for Python KWS with `audioBase64`)

—

## Installation

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

—

## How to Run

Option A — Quick Test (Front)

```
python -m http.server 5500
```
Open `http://localhost:5500/index.html`, allow mic/cam, test Gestures + KWS.

Option B — Web Panel (API)

- Script:
```
tools\run_api.ps1
```
Opens `http://127.0.0.1:8000/front`.

- Manual:
```
uvicorn src.detector_gestos.api:app --reload
```

Option C — CLI (OpenCV window)

```
python -m src.detector_gestos.main
```

—

## Training

Gestures (Python)

```
python training\train_model.py
```
Interactive trainer (capture + train):
```
python -m src.detector_gestos.train_gesture
```

KWS (Voice)

In Browser: front converts `audioBase64` → `spectrogram` and trains in TF.js.

In Python (final model):
```
python training\train_kws_model.py
```
- Accepts `samples[].spectrogram` directly.
- Accepts `audioBase64` (WebM/Opus) if ffmpeg is in PATH (see `docs/KWS-FFMPEG.md`).

—

## ESP32 Output

1) Arduino IDE → `esp32_sketch/esp32_controller.ino` → upload.
2) Pair “Controle de Gestos IA”.
3) `config.json`: `usar_serial: true`, set `serial_port` (e.g. `COM5`).
4) In the panel, switch output to ESP32.

—

## Configuration (`config.json`)

- Serial: `usar_serial`, `serial_port`, `serial_baudrate`
- Camera: `indice_camera`, `camera_width`, `camera_height`, `camera_fps`
- Gestures: `usar_modelo_gesto`, `gesto_modelo_path`, `gesto_labels`, `gesto_confianca_minima`, `frames_confirmacao_gesto`
- KWS: `usar_kws`, `kws_modelo_path`, `kws_labels_path`, `kws_confianca_minima`, `audio_input_device_index`
- Maps: `mapeamento_gestos`, `mapeamento_kws`
- Preview: `preview_max_fps`, `jpeg_quality`

—

## KWS Datasets & Formats

- `kws-samples.json` with `samples[].spectrogram` → ready (web/Python)
- `kws-dataset.json`/`kws-samples.json` with `samples[].audioBase64` → web converts; Python requires `ffmpeg`.
See `docs/KWS-FFMPEG.md`.

—

## FAQ / Troubleshooting

- KWS always predicts “pause”?
  - Retrain after fixing `inputShape`. Prefer collecting/training in the same frontend (web) or train in Python.
- “ffmpeg not found” (Python KWS)?
  - Install via winget/choco/scoop, reopen terminal; check `ffmpeg -version`.
- Camera won’t open?
  - Adjust `indice_camera`.
- ESP32 unavailable?
  - Check `serial_port` and connection; panel falls back to PC when serial is unavailable.
- Mic/cam denied?
  - Serve via `localhost` (don’t open file directly), allow permissions in the browser.

—

## Privacy

Audio/video are processed locally. The panel runs on `localhost`; data isn’t sent to external servers.

—

## Code Style

- JS/CSS/HTML: Prettier (`.prettierrc.json`)
- Python: Black (`pyproject.toml`). Apply with `pip install black && black .`

—

## Contributing

Issues and PRs are welcome. Suggestions: panel improvements, KWS collection/training, more actions/integrations, gesture detector tuning.
