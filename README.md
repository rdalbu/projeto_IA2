# Controle de Mídia por Gestos com IA e ESP32

Este projeto permite controlar a reprodução de mídia (play/pause, próxima/anterior) em qualquer dispositivo com Bluetooth (como celular, tablet ou smart TV) usando gestos de mão capturados por uma webcam e/ou palavras‑chave (KWS) via microfone.

O sistema utiliza Inteligência Artificial para reconhecer os gestos e um microcontrolador ESP32 para enviar os comandos como se fosse um teclado Bluetooth, tornando-o universalmente compatível.

<!-- Adicionar um GIF de demonstração aqui -->
<!-- ![Demonstração do Projeto](caminho/para/seu/gif.gif) -->

---

## Visão Geral

O projeto combina visão computacional e hardware para criar um controle de mídia intuitivo. É ideal para situações onde acessar fisicamente o dispositivo é inconveniente (exercícios, cozinha, TV distante, etc.).

Arquitetura (pipeline):

`Webcam` → `Python (OpenCV)` → `Reconhecimento de IA (TensorFlow/Keras + MediaPipe Hands)` → `Fila de Comandos` → `Saída via Serial (ESP32)` ou `Teclas Locais` → `Dispositivo Alvo`

Opcional: `Microfone` → `KWS (voz)` → `Fila de Comandos`.

### Funcionalidades

- Reconhecimento de gestos em tempo real (MediaPipe Hands + Keras)
- KWS (voz) opcional com MFCC e modelo Keras
- Controle via Bluetooth (ESP32 como teclado BLE) ou teclas locais (pyautogui/teclas multimídia)
- Interface de Linha de Comando (janela OpenCV) e API + Painel Web (preview MJPEG, overlay e log)
- Sistema de treinamento completo (web para coleta + scripts Python para treino final)

---

## Requisitos

### Hardware
- Webcam (qualquer padrão)
- ESP32 (ex.: NodeMCU‑32S ou similar)

### Software
- Python 3.8+
- Arduino IDE
- Git (opcional)

---

## SETUP: Instalação e Configuração

Siga estes 5 passos para preparar todo o ambiente.

### Passo 1: Obter o Projeto

Clone este repositório ou baixe o ZIP:

```sh
git clone https://github.com/rdalbu/projeto_IA2.git
```

### Passo 2: Configurar o Ambiente Python (Recomendado)

Para evitar conflitos de pacotes, use um ambiente virtual.

1. Abra um terminal na pasta raiz do projeto.
2. Crie o ambiente virtual (uma vez):
   ```sh
   python -m venv .venv
   ```
3. Ative o ambiente virtual (todas as vezes que usar):
   ```sh
   # Windows (PowerShell/CMD)
   .\.venv\Scripts\activate
   ```
4. Instale as dependências:
   ```sh
   pip install -r requirements.txt
   ```

### Passo 3: Preparar o ESP32

1. Abra a Arduino IDE.
2. Instale a biblioteca `BleKeyboard` (T‑vK) em `Tools > Manage Libraries...`.
3. Abra `esp32_sketch/esp32_controller.ino`.
4. Selecione a placa/porta e faça o upload.

### Passo 4: Parear o Bluetooth

1. Com o ESP32 ligado, procure novos dispositivos Bluetooth.
2. Pareie com **"Controle de Gestos IA"**.

### Passo 5: Configurar `config.json`

- Ajuste `serial_port` (ex.: "COM3", "COM5"), `usar_serial`, `indice_camera`, resoluções e FPS.
- Caminhos dos modelos: `gesto_modelo_path`, `kws_modelo_path`, `kws_labels_path`.
- Labels e mapeamentos: `gesto_labels`, `kws_labels`, `mapeamento_gestos`, `mapeamento_kws`.

---

## USO: Executando a Aplicação

### Modo 1 — CLI com janela OpenCV

1. Conecte o ESP32 (se for usar Serial) e ative o venv.
2. Execute:
   ```sh
   python -m src.detector_gestos.main
   ```
3. Uma janela com a imagem da câmera abrirá; o reconhecimento começa automaticamente. Comandos são enviados via serial (se habilitada) ou localmente.

### Modo 2 — API + Painel Web

1. Inicie a API:
   ```sh
   uvicorn src.detector_gestos.api:app --reload
   ```
2. Abra o painel em `http://127.0.0.1:8000/front`.
3. No painel você pode iniciar/parar a IA, habilitar KWS (microfone), alternar overlay e escolher saída (PC x ESP32).

---

## AVANÇADO: Treinando Seus Próprios Modelos

### Fase 1: Coleta de Dados e Teste Rápido (Navegador)

Use a interface web para coletar amostras e treinar um modelo temporário (feedback imediato).

1. Inicie um servidor local na raiz: `python -m http.server`.
2. Abra `index.html` no navegador.
3. Siga as instruções na página para:
   - Definir nomes dos seus gestos/palavras.
   - Gravar várias amostras por classe.
   - Treinar um modelo de teste rápido (no navegador).
   - Testar em tempo real.
4. Exporte os dados para treino final:
   - Use “Exportar Dataset” para salvar `gesture-dataset.json` e `kws-samples.json` na pasta raiz do projeto.

### Fase 2: Treinamento do Modelo Final (Terminal)

1. Gestos (Keras):
   ```sh
   python treinamento\train_model.py
   ```
2. KWS (voz):
   ```sh
   python treinamento\train_kws_model.py
   ```
Ambos geram modelos em `models/`.

### Fase 3: Atualizar a Configuração

1. Abra `config.json`.
2. Atualize `gesto_labels`, `kws_labels` e os mapeamentos `mapeamento_gestos`/`mapeamento_kws`.

---

## Notas Importantes sobre KWS (voz)

Há dois formatos de dataset KWS aceitos pelo trainer Python:

1) `kws-samples.json` com `samples[].spectrogram` (recomendado)
- Treina direto, não requer ffmpeg.

2) `kws-samples.json` com `samples[].audioBase64` (gravado no navegador)
- Na prática, costuma ser WebM/Opus (mesmo que o MIME diga `audio/wav`).
- Requer ffmpeg no PATH para converter para WAV antes de extrair MFCC.
- O script detecta o formato e indica o que fazer.

#### Converter audioBase64 → espectrograma (para treino no navegador)

Se você exportou um arquivo com `samples[].audioBase64` (gravação bruta), converta para espectrogramas 2D compatíveis com o treinador web:

```sh
python treinamento\convert_kws_audio_to_spectrogram.py -i kws-samples.json -o kws-samples-spectrogram.json
```

- Para amostras WebM/Opus (MediaRecorder), é necessário ter `ffmpeg` no PATH.
- O arquivo de saída (`kws-samples-spectrogram.json`) pode ser importado no navegador (index.html) para treinar diretamente.

### Como instalar o FFmpeg no Windows

- Winget (procure um ID disponível):
  - `winget source update`
  - `winget search ffmpeg`
  - `winget install --id Gyan.FFmpeg -e`
- Chocolatey (Admin): `choco install ffmpeg -y`
- Scoop:
  - `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`
  - `iwr -useb get.scoop.sh | iex`
  - `scoop install ffmpeg`
- Manual: baixe um build estático, extraia em `C:\ffmpeg` e adicione `C:\ffmpeg\bin` ao PATH.
- Verifique com `ffmpeg -version`.

---

## Troubleshooting (Solução de Problemas)

- “CRITICAL ERROR ao conectar na porta serial…”
  - Verifique se o ESP32 está conectado e se a COM em `config.json` é a mesma da Arduino IDE.

- “Não foi possível abrir a câmera…”
  - Confirme se a webcam funciona. Se tiver mais de uma, ajuste `indice_camera` (0, 1, 2…).

- Gestos com baixa precisão
  - Melhore a iluminação.
  - Diminua `gesto_confianca_minima`.
  - Treine com mais amostras e condições variadas.

- KWS indicando falta de ffmpeg
  - Instale o ffmpeg (ou reexporte o dataset em formato de espectrogramas no navegador).

---

## Contribuições

Contribuições são bem-vindas! Abra uma issue para relatar bugs ou sugerir melhorias.
