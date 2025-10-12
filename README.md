# Controle de Mídia por Gestos com IA e ESP32

Este projeto permite controlar a reprodução de mídia (play/pause, próxima/anterior) em qualquer dispositivo com Bluetooth (como um celular, tablet ou smart TV) usando gestos de mão capturados por uma webcam.

O sistema utiliza uma inteligência artificial para reconhecer os gestos e um microcontrolador ESP32 para enviar os comandos como se fosse um teclado Bluetooth, tornando-o universalmente compatível.

## Funcionalidades

- **Reconhecimento de Gestos em Tempo Real:** Usa MediaPipe e TensorFlow/Keras para alta precisão.
- **Controle Universal via Bluetooth:** O ESP32 atua como um teclado de mídia BLE, compatível com Android, iOS, Windows, macOS, etc.
- **Interface de Linha de Comando:** Execução simples e direta com feedback visual através de uma janela do OpenCV.
- **Sistema de Treinamento Completo:** Inclui uma interface web para coletar dados de novos gestos e scripts para treinar seu próprio modelo de IA.

## Como Funciona

A arquitetura do sistema segue este fluxo:

`Webcam` → `Python (OpenCV)` → `Reconhecimento de IA (TensorFlow)` → `Comando via Porta Serial` → `ESP32` → `Comando via Bluetooth` → `Dispositivo Alvo (Celular, etc.)`

## Requisitos de Hardware

- Uma webcam conectada ao seu computador.
- Um microcontrolador ESP32.

---


## SETUP: Instalação e Configuração

Siga estes 4 passos para preparar todo o ambiente.

### Passo 1: Baixar o Projeto

Clone ou baixe este repositório para o seu computador.

### Passo 2: Configurar o Ambiente Python (Recomendado)

Para evitar conflitos de pacotes, é altamente recomendado usar um ambiente virtual.

1.  **Abra um terminal** na pasta raiz do projeto.
2.  **Crie o ambiente virtual** (só precisa fazer isso uma vez):
    ```sh
    python -m venv .venv
    ```
3.  **Ative o ambiente virtual** (precisa fazer isso toda vez que for usar o projeto):
    ```sh
    # No Windows (PowerShell)
    .\.venv\Scripts\activate
    ```
    *Você saberá que funcionou quando vir `(.venv)` no início do seu terminal.*

4.  **Instale as dependências** com o ambiente ativo:
    ```sh
    pip install -r requirements.txt
    ```

### Passo 3: Preparar o ESP32

1.  **Abra a Arduino IDE**.
2.  **Instale a Biblioteca:** Vá em `Tools > Manage Libraries...` e procure e instale a biblioteca `BleKeyboard` de T-vK.
3.  **Carregue o Sketch:** Abra o arquivo `esp32_sketch/esp32_controller.ino` na Arduino IDE.
4.  **Faça o Upload:** Conecte seu ESP32 ao computador, selecione a placa e a porta COM correta em `Tools`, e clique no botão de Upload (seta para a direita).

### Passo 4: Parear o Bluetooth

1.  Com o ESP32 ligado, pegue seu dispositivo de mídia (celular, tablet, etc.).
2.  Procure por novos dispositivos Bluetooth.
3.  Pareie com o dispositivo chamado **"Controle de Gestos IA"**.

---


## USO: Executando a Aplicação

Com o setup concluído, siga os passos abaixo para usar o controle de gestos.

1.  **Conecte o ESP32** ao computador (para que a porta serial seja reconhecida).
2.  **Ative o Ambiente Virtual** (se não estiver ativo):
    ```sh
    .\.venv\Scripts\activate
    ```
3.  **Configure a Porta Serial**:
    - Abra o arquivo `config.json`.
    - Encontre a chave `"serial_port"` e altere o valor para a porta COM que seu ESP32 está usando (ex: `"COM3"`, `"COM5"`, etc.).
    - Garanta que `"usar_serial"` esteja como `true`.
4.  **Execute o Programa Principal**:
    No terminal (com o ambiente ativo), execute:
    ```sh
    python -m src.detector_gestos.main
    ```
5.  Uma janela com a imagem da sua câmera se abrirá, e o reconhecimento de gestos começará a funcionar.

---


## AVANÇADO: Treinando Seus Próprios Gestos

Se quiser adicionar novos gestos ou melhorar a precisão, siga estas fases.

### Fase 1: Coleta de Dados

1.  **Inicie o Servidor Web:** No terminal (na pasta raiz do projeto), execute:
    ```sh
    python -m http.server
    ```
2.  **Acesse a Interface:** Abra seu navegador e vá para `http://localhost:8000`.
3.  **Grave as Amostras:** Na página, defina os nomes dos seus gestos e use os controles para gravar dezenas de amostras para cada um.
4.  **Exporte e Salve:** Ao final, clique em **"Exportar Dataset"**. Salve o arquivo `gesture-dataset.json` na **pasta raiz** do projeto.

### Fase 2: Treinamento do Modelo

1.  Com o `gesture-dataset.json` na pasta raiz, execute o script de treinamento:
    ```sh
    python treinamento\train_model.py
    ```
2.  Este script usará seu dataset para gerar um novo modelo de IA em `models/meu_modelo/hand-gesture.h5`.

### Fase 3: Atualizar a Configuração

1.  Abra o `config.json`.
2.  Atualize a lista `"gesto_labels"` para que contenha os nomes exatos dos seus novos gestos, na mesma ordem em que foram gravados.
3.  Adicione o mapeamento dos novos gestos em `"mapeamento_gestos"`.

Após esses passos, ao executar o programa principal novamente, ele estará usando seu novo modelo treinado.
