API + Painel (opcional)

Descrição

- Além do modo CLI (janela OpenCV), o projeto possui uma API FastAPI com painel web para preview da câmera (MJPEG), alternar overlay, alternar saída (PC x ESP32) e ver eventos de gesto/voz em tempo real.

Como usar

1. Ajuste `config.json` conforme seu ambiente (câmera, serial, modelos, etc.).
2. Inicie a API: `uvicorn src.detector_gestos.api:app --reload`
3. Abra o painel: `http://127.0.0.1:8000/front`
4. Use os controles para iniciar/parar IA, habilitar KWS (microfone), alternar overlay e saída.

Endpoints úteis

- `GET /start` — inicia o runner em background
- `GET /stop` — para o runner
- `GET /state` — estado do runner
- `GET /output/state` e `POST /output/set?mode=serial|local` — modo de saída
- `GET /kws/state`, `POST /kws/enable`, `POST /kws/disable` — controle do KWS
- `GET /frame.jpg` — último frame (JPEG)
- `GET /stream` — preview MJPEG
- `GET /overlay/state`, `POST /overlay/enable`, `POST /overlay/disable` — overlay na câmera
- `WS /ws` — eventos de gesto/KWS em tempo real

Observações

- O painel (front) está em `server/front/` e é servido automaticamente em `/front`.
