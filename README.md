# Detector de Gestos para Controle de Mídia

Este projeto permite controlar a reprodução de mídias (como Spotify, YouTube, etc.) no seu computador através de gestos com a mão, capturados por uma webcam.

## Funcionalidades

- **Play / Pause:** Gesto de pinça com o polegar e o indicador.
- **Próxima Faixa:** Deslize a mão com dois dedos levantados para a direita.
- **Faixa Anterior:** Deslize a mão com dois dedos levantados para a esquerda.

## Estrutura do Projeto

O código é organizado de forma modular para facilitar a manutenção e o entendimento:

- **`main.py`**: O ponto de entrada da aplicação. Orquestra a captura de vídeo, a detecção da mão e o reconhecimento do gesto.
- **`hand_detector.py`**: Contém a classe `DetectorMaos`, responsável por usar o MediaPipe para encontrar a mão na imagem e extrair as coordenadas dos seus pontos.
- **`gesture_recognizer.py`**: Abriga a classe `GestureRecognizer`, que analisa os pontos da mão para interpretar qual gesto (pinça, deslize, etc.) está sendo realizado.
- **`constants.py`**: Define constantes para os pontos de referência da mão, tornando o código mais legível e evitando "números mágicos".
- **`config.json`**: Arquivo de configuração para ajustar parâmetros de sensibilidade e comportamento sem alterar o código.

## Tecnologias Utilizadas

- **Python 3.10+**
- **OpenCV:** Para captura e processamento de vídeo da webcam.
- **MediaPipe:** Para a detecção e rastreamento dos pontos da mão.
- **PyAutoGUI:** Para simular os comandos de teclado (teclas de mídia).

## Instalação

1. **Clone ou baixe este repositório.**

2. **Navegue até a pasta do projeto:**
   ```bash
   cd projeto_IA2
   ```

3. **Instale as dependências:**
   É recomendado criar um ambiente virtual (virtual environment) antes de instalar.
   ```bash
   pip install -r requirements.txt
   ```

## Configuração

Antes de executar, você pode ajustar os parâmetros no arquivo `config.json`:

- `indice_camera`: O índice da sua webcam. `0` geralmente é a padrão.
- `confianca_deteccao`: Nível de confiança mínimo (0.0 a 1.0) para a detecção da mão.
- `confianca_rastreamento`: Nível de confiança mínimo (0.0 a 1.0) para o rastreamento da mão.
- `sensibilidade_deslize_pixels`: Distância mínima (em pixels) para registrar um gesto de deslize.
- `pinch_threshold_pixels`: Distância máxima (em pixels) entre o polegar e o indicador para registrar uma pinça.
- `frames_confirmacao_gesto`: Número de frames que um gesto precisa ser mantido para ser confirmado.
- `intervalo_entre_comandos_segundos`: Tempo de espera (em segundos) antes que um novo comando possa ser enviado.
- `mapeamento_gestos`: Mapeia os gestos detectados para as teclas do `pyautogui`.

## Como Usar

1.  Certifique-se de que um aplicativo de mídia (Spotify, etc.) esteja aberto e em foco.
2.  Execute o script principal a partir da pasta raiz do projeto:
    ```bash
    python -m src.detector_gestos.main
    ```
3.  Uma janela com a imagem da sua webcam aparecerá, e o detector começará a funcionar.

## Solução de Problemas

- **Webcam não encontrada:** Verifique se o `indice_camera` no `config.json` está correto.
- **Gestos não reconhecidos:** Tente ajustar os valores de confiança e sensibilidade no `config.json`.
- **Comandos de mídia não funcionam:** Certifique-se de que o aplicativo de mídia esteja em foco (a janela do aplicativo esteja selecionada).