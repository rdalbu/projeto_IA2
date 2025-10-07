# Detector de Gestos para Controle de Mídia

Este projeto permite controlar a reprodução de mídias (como Spotify, YouTube, etc.) no seu computador através de gestos com a mão, capturados por uma webcam.

## Funcionalidades

- **Play / Pause:** Feche a mão para pausar ou dar play.
- **Próxima Faixa:** Deslize a mão com dois dedos levantados para a direita.
- **Faixa Anterior:** Deslize a mão com dois dedos levantados para a esquerda.

## Tecnologias Utilizadas

- **Python 3.10+**
- **OpenCV:** Para captura e processamento de vídeo da webcam.
- **MediaPipe:** Para a detecção e rastreamento dos pontos da mão.
- **PyAutoGUI:** Para simular os comandos de teclado (teclas de mídia).

## Instalação

1. **Clone ou baixe este repositório.**

2. **Navegue até a pasta do projeto:**
   ```bash
   cd Detector_Gestos_Maos
   ```

3. **Instale as dependências:**
   É recomendado criar um ambiente virtual (virtual environment) antes de instalar.
   ```bash
   pip install -r requirements.txt
   ```

## Configuração

Antes de executar, você pode ajustar os parâmetros de sensibilidade e comportamento no arquivo `config.json`.

- `indice_camera`: O índice da sua webcam. `0` geralmente é a padrão. Mude para `1` ou `2` se tiver múltiplas câmeras.
- `confianca_deteccao`: Nível de confiança mínimo (0.0 a 1.0) para a detecção inicial da mão.
- `confianca_rastreamento`: Nível de confiança mínimo (0.0 a 1.0) para o rastreamento da mão entre frames.
- `sensibilidade_deslize_pixels`: A distância mínima (em pixels) que a mão precisa percorrer para registrar um gesto de deslize.
- `frames_confirmacao_gesto`: O número de frames que um gesto estático precisa ser mantido para ser confirmado.
- `intervalo_entre_comandos_segundos`: O tempo de espera (em segundos) antes que um novo comando possa ser enviado.
- `mapeamento_gestos`: Mapeia os gestos detectados para as teclas do `pyautogui`.

## Como Usar

1.  Certifique-se de que um aplicativo de mídia (Spotify, etc.) esteja aberto e em foco.
2.  Execute o script principal a partir da pasta raiz do projeto:
    ```bash
    python Detector_Mao/main.py
    ```
3.  Uma janela com a imagem da sua webcam aparecerá, e o detector começará a funcionar.

## Solução de Problemas

- **Webcam não encontrada:** Verifique se o `indice_camera` no arquivo `config.json` está correto. Se você tiver apenas uma webcam, o valor `0` geralmente funciona. Se você tiver várias, tente `1`, `2`, etc.
- **Gestos não reconhecidos:** Tente ajustar os valores de `confianca_deteccao` e `confianca_rastreamento` no arquivo `config.json`. Valores mais baixos podem tornar a detecção mais fácil, mas também podem levar a mais falsos positivos.
- **Comandos de mídia não funcionam:** Certifique-se de que o aplicativo de mídia esteja em foco (a janela do aplicativo esteja selecionada) para que ele possa receber os comandos do teclado.
