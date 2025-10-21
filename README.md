# Controle de Mídia por Gestos e Voz (IA + ESP32)

Controle de mídia (play/pause, próxima, anterior) usando gestos de mão (webcam) e/ou palavras‑chave (microfone). A saída pode ser local (teclas multimídia no PC) ou via ESP32 como teclado Bluetooth (para celular/TV).

—

## Quick Start

1) Windows + PowerShell (na pasta do projeto):
```
tools\run_api.ps1
```
2) Abra `http://127.0.0.1:8000/front` e ative Câmera/KWS. 
3) Opcional: ligue o ESP32 e selecione “ESP32” em “Saída de Comandos”.

—

## Tabela de Conteúdos

- [Visão Geral](#visão-geral)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Como Testar](#como-testar)
- [Treino de Modelos](#treino-de-modelos)
- [ESP32](#esp32-saída-bluetooth)
- [Configuração](#configuração-configjson)
- [Datasets KWS](#datasets-e-formatos-kws)
- [FAQ / Troubleshooting](#faq--troubleshooting)
- [Privacidade](#privacidade)
- [Formatação do Código](#formatação-do-código)
- [Contribuindo](#contribuindo)

—

## Visão Geral

Pipeline

`Webcam` → `MediaPipe Hands` → `Keras` → `Comandos` → `Serial (ESP32)` ou `Teclas Locais`

Opcional: `Microfone` → `KWS (voz)` → `Comandos`.

Recursos

- Gestos em tempo real (MediaPipe + Keras)
- KWS (voz) no navegador e em Python
- Painel web (FastAPI): preview, overlay, KWS on/off, saída PC x ESP32
- Front “Teste Rápido” (`index.html`): coleta/treino no navegador
- Scripts Python de treino (gestos + KWS)

—

## Requisitos

- Windows 10/11 (recomendado) 
- Python 3.10/3.11 (3.8+ funciona) 
- PowerShell
- Arduino IDE (se usar ESP32)
- ffmpeg (somente se treinar KWS com `audioBase64` no Python)

—

## Instalação

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

—

## Como Testar

Opção A — Teste Rápido (Front)

```
python -m http.server 5500
```
Abra `http://localhost:5500/index.html`, autorize microfone/câmera e teste Gestos/KWS.

Opção B — Painel Web (API)

- Script:
```
tools\run_api.ps1
```
Abre `http://127.0.0.1:8000/front`.

- Manual:
```
uvicorn src.detector_gestos.api:app --reload
```

Opção C — CLI (janela OpenCV)

```
python -m src.detector_gestos.main
```

—

## Treino de Modelos

Gestos (Python)

```
python training\train_model.py
```
Treinador interativo (coleta + treino):
```
python -m src.detector_gestos.train_gesture
```

KWS (Voz)

No navegador: o front converte `audioBase64` → `spectrogram` e treina no TF.js.

No Python (modelo final):
```
python training\train_kws_model.py
```
- Aceita `samples[].spectrogram` diretamente.
- Aceita `audioBase64` (WebM/Opus) com ffmpeg no PATH (docs/KWS-FFMPEG.md).

—

## ESP32 (Saída Bluetooth)

1) Arduino IDE → `esp32_sketch/esp32_controller.ino` → upload.
2) Pareie “Controle de Gestos IA”.
3) `config.json`: `usar_serial: true`, `serial_port: "COMx"`.
4) No painel: “Saída de Comandos” → ESP32.

—

## Configuração (`config.json`)

- Serial: `usar_serial`, `serial_port`, `serial_baudrate`
- Câmera: `indice_camera`, `camera_width`, `camera_height`, `camera_fps`
- Gestos: `usar_modelo_gesto`, `gesto_modelo_path`, `gesto_labels`, `gesto_confianca_minima`, `frames_confirmacao_gesto`
- KWS: `usar_kws`, `kws_modelo_path`, `kws_labels_path`, `kws_confianca_minima`, `audio_input_device_index`
- Mapas: `mapeamento_gestos`, `mapeamento_kws`
- Preview: `preview_max_fps`, `jpeg_quality`

—

## Datasets e Formatos (KWS)

- `kws-samples.json` com `samples[].spectrogram` → pronto (web/Python)
- `kws-dataset.json`/`kws-samples.json` com `samples[].audioBase64` → web converte; no Python requer `ffmpeg`.
Veja a seção "KWS + FFmpeg (Guia Rápido)".

—

## FAQ / Troubleshooting

- O KWS só acerta “pause”? 
  - Re‑treine após corrigir `inputShape`. Prefira coletar/treinar no mesmo frontend (web) ou treinar no Python.
- “ffmpeg não encontrado” no KWS Python?
  - Instale via winget/choco/scoop e reabra o terminal; verifique `ffmpeg -version`.
- Câmera não abre?
  - Ajuste `indice_camera` no `config.json`.
- ESP32 não aparece?
  - Confirme `serial_port` e conexão; no painel, o modo volta a PC se a serial não estiver disponível.
- Microfone/câmera bloqueados?
  - Teste em `localhost` (não abra `index.html` direto), e permita as permissões no navegador.

—

## Privacidade

Vídeo e áudio são processados localmente. O painel usa `localhost`, e os dados não são enviados para servidores externos.

—

## Formatação do Código

- JS/CSS/HTML: Prettier (`.prettierrc.json`)
- Python: Black (`pyproject.toml`). Para aplicar: `pip install black && black .`

—

## Contribuindo

Issues e PRs são bem‑vindos. Sugestões: melhorias no painel, coleta/treino de KWS, integração com mais ações e ajustes no detector de gestos.

—

## Detalhes da API/Painel

- Iniciar API: `uvicorn src.detector_gestos.api:app --reload`
- Painel: `http://127.0.0.1:8000/front`
- Endpoints úteis:
  - `GET /start` — inicia o runner
  - `GET /stop` — para o runner
  - `GET /state` — estado do runner
  - `GET /output/state` e `POST /output/set?mode=serial|local` — modo de saída
  - `GET /kws/state`, `POST /kws/enable`, `POST /kws/disable` — controle do KWS
  - `GET /frame.jpg` — último frame (JPEG)
  - `GET /stream` — preview MJPEG
  - `GET /overlay/state`, `POST /overlay/enable`, `POST /overlay/disable` — overlay
  - `WS /ws` — eventos de gesto/KWS em tempo real

—

## KWS + FFmpeg (Guia Rápido)

Resumo
- Formatos aceitos:
  - `kws-samples.json` com `samples[].spectrogram` (recomendado): treina direto (web/Python).
  - `kws-samples.json` com `samples[].audioBase64` (WebM/Opus do navegador): requer ffmpeg para converter antes de extrair MFCC no Python.

Como resolver
1) Instalar ffmpeg e treinar normalmente no Python; ou
2) No navegador (index.html), exportar dataset já com `samples[].spectrogram` e treinar no próprio front.

Instalação do FFmpeg (Windows)
- Winget:
  - `winget source update`
  - `winget search ffmpeg`
  - `winget install --id Gyan.FFmpeg -e`
- Chocolatey (Admin): `choco install ffmpeg -y`
- Scoop:
  - `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`
  - `iwr -useb get.scoop.sh | iex`
  - `scoop install ffmpeg`
- Manual: baixe um build estático, extraia em `C:\ffmpeg` e adicione `C:\ffmpeg\bin` ao PATH.

Verificação
- Feche/abra o terminal e rode: `ffmpeg -version`

Treino (Python)
- `python training\train_kws_model.py`
