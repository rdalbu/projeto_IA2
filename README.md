# Controle de Mídia por Gestos com IA e ESP32

Este projeto permite controlar a reprodução de mídia (play/pause, próxima/anterior) em qualquer dispositivo com Bluetooth (como um celular, tablet ou smart TV) usando gestos de mão capturados por uma webcam.

O sistema utiliza uma inteligência artificial para reconhecer os gestos e um microcontrolador ESP32 para enviar os comandos como se fosse um teclado Bluetooth, tornando-o universalmente compatível.

<!-- Adicionar um GIF de demonstração aqui -->
<!-- ![Demonstração do Projeto](caminho/para/seu/gif.gif) -->


---

## ➤ Visão Geral

O projeto combina visão computacional e hardware para criar um controle de mídia intuitivo. Ele é ideal para situações onde o acesso físico ao dispositivo de mídia é inconveniente, como durante exercícios, cozinhando ou quando o dispositivo está distante.

### Como Funciona

A arquitetura do sistema segue este fluxo:

`Webcam` → `Python (OpenCV)` → `Reconhecimento de IA (TensorFlow)` → `Comando via Porta Serial` → `ESP32` → `Comando via Bluetooth` → `Dispositivo Alvo (Celular, etc.)`

### Funcionalidades

- **Reconhecimento de Gestos em Tempo Real:** Usa MediaPipe e TensorFlow/Keras para alta precisão.
- **Controle Universal via Bluetooth:** O ESP32 atua como um teclado de mídia BLE, compatível com Android, iOS, Windows, macOS, etc.
- **Interface de Linha de Comando:** Execução simples e direta com feedback visual através de uma janela do OpenCV.
- **Sistema de Treinamento Completo:** Inclui uma interface web para coletar dados de novos gestos e scripts para treinar seu próprio modelo de IA.

---

## ✔ Requisitos

Antes de começar, garanta que você tenha os seguintes itens.

### Hardware

- **Webcam:** Qualquer webcam padrão conectada ao seu computador.
- **Microcontrolador ESP32:** Um modelo de desenvolvimento como o NodeMCU-32S ou similar.

### Software

- **Python 3.8+:** [Link para download](https://www.python.org/downloads/).
- **Arduino IDE:** [Link para download](https://www.arduino.cc/en/software).
- **Git:** (Opcional, mas recomendado para clonar o projeto) [Link para download](https://git-scm.com/downloads).

---

## ⚙️ SETUP: Instalação e Configuração

Siga estes 5 passos para preparar todo o ambiente.

### Passo 1: Obter o Projeto

Clone este repositório para o seu computador usando Git:

```sh
git clone <URL_DO_REPOSITORIO>
```

Ou baixe o arquivo ZIP e extraia-o.

### Passo 2: Configurar o Ambiente Python (Recomendado)

Para evitar conflitos de pacotes, é altamente recomendado usar um ambiente virtual.

1.  **Abra um terminal** na pasta raiz do projeto.
2.  **Crie o ambiente virtual** (só precisa fazer isso uma vez):
    ```sh
    python -m venv .venv
    ```
3.  **Ative o ambiente virtual** (precisa fazer isso toda vez que for usar o projeto):
    ```sh
    # No Windows (PowerShell/CMD)
    .\.venv\Scripts\activate
    ```
    *Você saberá que funcionou quando vir `(.venv)` no início do seu terminal.*

### Passo 3: Instalar as Dependências

Com o ambiente virtual ativo, instale todas as bibliotecas Python necessárias:

```sh
pip install -r requirements.txt
```

### Passo 4: Preparar o ESP32

1.  **Abra a Arduino IDE**.
2.  **Instale a Biblioteca:** Vá em `Tools > Manage Libraries...` e procure e instale a biblioteca `BleKeyboard` de T-vK.
3.  **Carregue o Sketch:** Abra o arquivo `esp32_sketch/esp32_controller.ino` na Arduino IDE.
4.  **Faça o Upload:** Conecte seu ESP32 ao computador, selecione a placa (`ESP32 Dev Module` ou similar) e a porta COM correta em `Tools`, e clique no botão de Upload (seta para a direita).

### Passo 5: Parear o Bluetooth

1.  Com o ESP32 ligado, pegue seu dispositivo de mídia (celular, tablet, etc.).
2.  Procure por novos dispositivos Bluetooth.
3.  Pareie com o dispositivo chamado **"Controle de Gestos IA"**.

---

## ▶️ USO: Executando a Aplicação

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

## 🧠 AVANÇADO: Treinando Seus Próprios Modelos

Se quiser adicionar novos gestos ou comandos de voz, siga as fases abaixo.

### Fase 1: Coleta de Dados e Teste Rápido (Navegador)

Use a interface web para coletar amostras e treinar um modelo temporário para feedback imediato.

1.  **Inicie a Interface Web:**
    - No terminal, na raiz do projeto, inicie um servidor local: `python -m http.server`.
    - Abra seu navegador e acesse: `http://localhost:8000`.

2.  **Na página, siga as instruções para:**
    - Definir os nomes dos seus gestos ou palavras-chave.
    - Gravar várias amostras para cada um.
    - Treinar um modelo de teste rápido.
    - Testar em tempo real no navegador.

3.  **Exporte os Dados para o Treino Final:**
    - Use os botões **"Exportar Dataset"** para salvar os arquivos `gesture-dataset.json` e `kws-samples.json` na **pasta raiz** do projeto.

### Fase 2: Treinamento do Modelo Final (Terminal)

Use os scripts Python para criar os modelos `.h5` que a aplicação principal utiliza.

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
2.  Atualize as listas `"gesto_labels"` e `"kws_labels"` com os nomes exatos dos seus novos gestos/palavras.
3.  Atualize os mapeamentos `"mapeamento_gestos"` e `"mapeamento_kws"` para associar cada classe a um comando (`"playpause"`, `"nexttrack"`, etc.).

---

## ❓ Troubleshooting (Solução de Problemas)

- **Erro: "ERRO CRÍTICO ao conectar na porta serial..."**
  - **Solução:** Verifique se o ESP32 está conectado ao computador. Confirme se a porta COM em `config.json` é a mesma que aparece na Arduino IDE. No Windows, você pode encontrá-la no "Gerenciador de Dispositivos".

- **Erro: "Não foi possível abrir a câmera..."**
  - **Solução:** Verifique se a webcam está conectada e funcionando. Se você tiver mais de uma câmera, altere o valor de `"indice_camera"` em `config.json` (tente 0, 1, 2, etc.).

- **Gestos não são reconhecidos com precisão:**
  - **Solução 1:** A iluminação do ambiente afeta muito a detecção. Tente em um local mais bem iluminado.
  - **Solução 2:** A confiança mínima pode estar muito alta. Tente diminuir o valor de `"gesto_confianca_minima"` em `config.json`.
  - **Solução 3:** Treine seu próprio modelo com mais amostras e em condições de iluminação variadas para maior robustez.

---

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir uma *issue* para relatar bugs ou sugerir melhorias.