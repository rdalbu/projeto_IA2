# AI Gesture Media Control with ESP32

This project lets you control media playback (play/pause, next/previous) on any Bluetooth‑enabled device (phone, tablet, smart TV, etc.) using hand gestures via webcam and/or voice keywords (KWS) via microphone.

The system uses computer vision and AI models (TensorFlow/Keras) to recognize gestures, and an ESP32 to send commands as if it were a Bluetooth keyboard, ensuring broad compatibility.

<!-- Add a demonstration GIF here -->
<!-- ![Project Demo](path/to/your/gif.gif) -->

---

## Overview

The project combines computer vision and hardware to create an intuitive media controller. It is ideal when physical access to the device is inconvenient (workouts, kitchen, distant TV, etc.).

Architecture (pipeline):

`Webcam` → `Python (OpenCV)` → `AI Recognition (TensorFlow/Keras + MediaPipe Hands)` → `Command Queue` → `Serial (ESP32)` or `Local Keys` → `Target Device`

Optional: `Microphone` → `KWS (voice)` → `Command Queue`.

### Features

- Real‑time gesture recognition (MediaPipe Hands + Keras)
- Optional KWS (voice) with MFCC + Keras model
- Outputs: Serial (ESP32 BLE Keyboard) or local media keys (pyautogui)
- CLI (OpenCV window) and API + Web Panel (MJPEG preview, overlay, real‑time log)
- Complete training flow (web collection + Python final training)

---

## Requirements

### Hardware
- Webcam
- ESP32 (e.g., NodeMCU‑32S)

### Software
- Python 3.8+
- Arduino IDE
- Git (optional)

---

## SETUP: Installation and Configuration

Follow these steps to set up the environment.

### Step 1: Get the Project

Clone or download ZIP:

```sh
git clone https://github.com/rdalbu/projeto_IA2.git
```

### Step 2: Python Environment (Recommended)

1. Open a terminal in the project root.
2. Create a virtual environment (once):
   ```sh
   python -m venv .venv
   ```
3. Activate it (every time):
   ```sh
   .\.venv\Scripts\activate
   ```
4. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

### Step 3: Prepare the ESP32

1. Open Arduino IDE.
2. Install `BleKeyboard` (T‑vK) in `Tools > Manage Libraries...`.
3. Open `esp32_sketch/esp32_controller.ino`.
4. Select board/port and upload.

### Step 4: Bluetooth Pairing

Pair the device named **"Controle de Gestos IA"**.

### Step 5: Configure `config.json`

Adjust `serial_port`, `usar_serial`, `indice_camera`, resolution/FPS, model paths, labels and mappings.

---

## USAGE

### Mode 1 — CLI (OpenCV window)

1. Connect ESP32 (if using serial) and activate the venv.
2. Run:
   ```sh
   python -m src.detector_gestos.main
   ```
3. A window will open with the camera preview; commands are sent via serial or locally.

### Mode 2 — API + Web Panel

1. Start the API:
   ```sh
   uvicorn src.detector_gestos.api:app --reload
   ```
2. Open `http://127.0.0.1:8000/front`.
3. Start/stop AI, enable KWS (mic), toggle overlay, choose output (PC vs ESP32).

---

## ADVANCED: Training Your Own Models

### Phase 1: Data Collection & Quick Test (Browser)

1. Start a local server in the root: `python -m http.server`.
2. Open `index.html` in the browser.
3. Follow the instructions to define classes, record samples, train quick models, and test live.
4. Export datasets: `gesture-dataset.json` and `kws-samples.json` (to the project root).

### Phase 2: Final Training (Python)

1. Gestures (Keras):
   ```sh
   python treinamento\train_model.py
   ```
2. KWS (voice):
   ```sh
   python treinamento\train_kws_model.py
   ```
Models are saved under `models/`.

### Phase 3: Update Configuration

Edit `config.json` to update `gesto_labels`, `kws_labels`, and the mappings `mapeamento_gestos`/`mapeamento_kws`.

---

## Important Notes about KWS

Two KWS dataset formats are supported:

1) `kws-samples.json` with `samples[].spectrogram` (recommended)
- Trains directly, no ffmpeg required.

2) `kws-samples.json` with `samples[].audioBase64` (browser recording)
- In practice, usually WebM/Opus (even if MIME says `audio/wav`).
- Requires ffmpeg in PATH to convert to WAV before MFCC extraction.
- The script detects the format and prints guidance.

#### Convert audioBase64 → spectrogram (for browser training)

If you exported a file with `samples[].audioBase64` (raw recordings), convert it to 2D spectrograms compatible with the web trainer:

```sh
python treinamento\convert_kws_audio_to_spectrogram.py -i kws-samples.json -o kws-samples-spectrogram.json
```

- For WebM/Opus (MediaRecorder) samples, `ffmpeg` must be available in PATH.
- The output file (`kws-samples-spectrogram.json`) can be imported in the browser (index.html) to train directly.

### Installing FFmpeg on Windows

- Winget (search an available ID):
  - `winget source update`
  - `winget search ffmpeg`
  - `winget install --id Gyan.FFmpeg -e`
- Chocolatey (Admin): `choco install ffmpeg -y`
- Scoop:
  - `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`
  - `iwr -useb get.scoop.sh | iex`
  - `scoop install ffmpeg`
- Manual: download a static build, extract to `C:\ffmpeg`, add `C:\ffmpeg\bin` to PATH.
- Verify with `ffmpeg -version`.

---

## Troubleshooting

- Serial errors: check connection and COM in `config.json`.
- Camera open failure: adjust `indice_camera` (0,1,2...).
- Poor gesture accuracy: improve lighting, lower `gesto_confianca_minima`, train more data.
- KWS ffmpeg warning: install ffmpeg or re‑export dataset as spectrograms in the browser.

---

## Contributions

Contributions are welcome! Please open an issue to report bugs or suggest improvements.
