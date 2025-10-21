KWS (voz) e FFmpeg — Guia Rápido

Resumo

- Dois formatos de dataset KWS são aceitos pelo projeto:
  - Espectrogramas: `kws-samples.json` com `samples[].spectrogram` (recomendado). Treina direto no Python, sem ffmpeg.
  - Áudio base64: `kws-samples.json` com `samples[].audioBase64` (geralmente WebM/Opus gravado pelo navegador). Requer ffmpeg no PATH para converter para WAV antes de extrair MFCC.

Mensagens comuns

- "Formato detectado: samples[].audioBase64 = WebM/Opus ..."
- "Dataset usa audioBase64 em WebM/Opus e o ffmpeg não está no PATH."

Como resolver

1. Instalar ffmpeg e treinar normalmente; ou
2. Reexportar pelo navegador (index.html), seção KWS → "Exportar Dataset" para gerar `samples[].spectrogram`.

Instalação do FFmpeg (Windows)

- Winget:
  - `winget source update`
  - `winget search ffmpeg`
  - `winget install --id Gyan.FFmpeg -e` (ou outro ID listado)
- Chocolatey (Admin):
  - Instalar Chocolatey:
    `Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))`
  - `choco install ffmpeg -y`
- Scoop:
  - `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`
  - `iwr -useb get.scoop.sh | iex`
  - `scoop install ffmpeg`
- Manual:
  - Baixe um build estático, extraia em `C:\ffmpeg` e adicione `C:\ffmpeg\bin` ao PATH do sistema.

Verificação

- Feche e reabra o PowerShell e rode `ffmpeg -version`.

Treino

- Garanta `pip install soundfile` no venv.
- Rode: `python treinamento\train_kws_model.py`.
