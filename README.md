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


## AVANÇADO: Treinando Seus Próprios Gestos e Voz

Se quiser adicionar novos comandos ou melhorar a precisão, o fluxo agora é unificado e dividido em duas fases principais: uma no navegador para testes rápidos e outra no terminal para gerar o modelo final.

### Fase 1: Coleta de Dados e Teste Rápido (no Navegador)

Nesta fase, você usa a interface web para coletar amostras e treinar um modelo temporário que funciona apenas no navegador, ideal para ter um feedback imediato.

1.  **Inicie a Interface Web:**
    - Abra um terminal na pasta raiz do projeto.
    - Inicie um servidor local com o comando: `python -m http.server`.
    - Abra seu navegador e acesse o endereço: `http://localhost:8000`.

2.  **Na página, você verá duas seções:** "Coleta e Teste de Gestos" e "Coleta e Teste de Voz (KWS)". O processo é o mesmo para ambas:
    - **Defina as Classes:** Digite os nomes dos seus gestos ou palavras-chave, separados por vírgula (ex: `subir,descer,neutro`).
    - **Grave as Amostras:** Selecione a classe/palavra no menu e grave várias amostras (recomenda-se 20 ou mais para cada uma).
    - **Treine o Modelo de Teste:** Clique em **"Treinar (Teste Rápido)"**. Isso treinará um modelo temporário no seu navegador.
    - **Teste em Tempo Real:** Marque a caixa **"Usar modelo de teste (após treinar)"** e faça os gestos ou fale as palavras. A área de "Predições" mostrará o resultado em tempo real.

3.  **Exporte os Dados para o Treino Final:**
    - Quando estiver satisfeito com a quantidade de amostras, use os botões **"Exportar Dataset"** em cada seção.
    - Salve os arquivos `gesture-dataset.json` (para gestos) e `kws-samples.json` (para voz) na **pasta raiz** do projeto.

### Fase 2: Treinamento do Modelo Final (no Terminal)

Depois de exportar os datasets, você usará os scripts Python para criar os modelos `.h5` que a aplicação principal realmente utiliza.

1.  **Treine o Modelo de Gestos:**
    - Certifique-se de que o `gesture-dataset.json` está na raiz do projeto.
    - No terminal (com o ambiente virtual ativo), execute:
      ```sh
      python treinamento\train_model.py
      ```

2.  **Treine o Modelo de Voz (KWS):**
    - Certifique-se de que o `kws-samples.json` está na raiz do projeto.
    - No terminal, execute:
      ```sh
      python treinamento\train_kws_model.py
      ```

Ambos os scripts salvarão os modelos finais na pasta `models/`.

### Fase 3: Atualizar a Configuração

1.  Abra o arquivo `config.json`.
2.  Atualize as listas `"gesto_labels"` e `"kws_labels"` para que contenham os nomes exatos dos seus novos gestos/palavras, na mesma ordem em que foram gravados.
3.  Atualize os mapeamentos `"mapeamento_gestos"` e `"mapeamento_kws"` para associar cada classe a um comando (ex: `"playpause"`, `"nexttrack"`).

Após esses passos, ao executar o programa principal (`python -m src.detector_gestos.main`), ele estará usando seus novos modelos treinados.
