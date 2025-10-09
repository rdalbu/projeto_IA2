# Projeto de Controle por Gestos com IA

Este projeto permite controlar o computador (ex: tocar e pausar músicas) através de gestos de mão customizados, treinados por você.

## Pré-requisitos

- Python 3.8+
- Um navegador web moderno (Chrome, Firefox)
- Uma webcam

## Instalação

1.  **Clone o repositório** (ou baixe o ZIP).
2.  **Instale as dependências** Python. Abra um terminal na pasta raiz do projeto e execute:
    ```bash
    pip install -r requirements.txt
    ```

## Fluxo de Trabalho

O projeto é dividido em três etapas:

### 1. Coleta de Dados (Navegador Web)

- **Objetivo:** Coletar amostras dos gestos que você quer que o sistema reconheça.
- **Como fazer:**
  1. Inicie um servidor web local na pasta raiz. O mais simples é usar Python:
     ```bash
     python -m http.server
     ```
  2. Abra o navegador e acesse `http://localhost:8000`.
  3. Defina os nomes das suas classes de gestos (ex: `pinca`, `passar`, `neutro`).
  4. Use os controles para gravar várias amostras de cada gesto.
  5. Ao final, clique em **"Exportar Dataset"** para baixar o arquivo `gesture-dataset.json`.

### 2. Treinamento do Modelo (Python)

- **Objetivo:** Usar as amostras coletadas para treinar um modelo de IA.
- **Como fazer:**
  1. Mova o arquivo `gesture-dataset.json` para a pasta raiz do projeto.
  2. No terminal, na pasta raiz, execute o script de treinamento:
     ```bash
     python train_model.py
     ```
  3. **Automação:** Este script agora faz duas coisas:
     - Cria o modelo principal `models/meu_modelo/hand-gesture.h5`.
     - **Exporta automaticamente** o modelo para o formato **TensorFlow.js** (`model.json` e `weights.bin`) na mesma pasta, garantindo que os entregáveis estejam sempre atualizados.

### 3. Execução e Controle (Python)

- **Objetivo:** Rodar o programa que usa a câmera para reconhecer seus gestos e controlar o computador.
- **Como fazer:**
  1. **Configure:** Verifique e ajuste o arquivo `config.json` conforme necessário (veja detalhes abaixo).
  2. **Execute:** No terminal, na pasta raiz, rode o programa principal:
     ```bash
     python -m src.detector_gestos.main
     ```
  3. Uma janela com a câmera se abrirá, e seus gestos passarão a controlar as ações mapeadas.

## Checklist de Testes

Para garantir que tudo funciona, siga este checklist:

- [ ] **1. Servidor Web:** O comando `python -m http.server` inicia sem erros.
- [ ] **2. Coleta de Dados:** A página `index.html` carrega no navegador e a imagem da câmera aparece.
- [ ] **3. Gravação de Gestos:** É possível gravar amostras para cada gesto e o contador de amostras aumenta.
- [ ] **4. Exportação do Dataset:** O botão "Exportar Dataset" gera e baixa o arquivo `gesture-dataset.json`.
- [ ] **5. Treinamento do Modelo:** O script `python train_model.py` executa até o fim, sem erros, e cria/atualiza os arquivos do modelo em `models/meu_modelo/`.
- [ ] **6. Execução Principal:** O comando `python -m src.detector_gestos.main` inicia e abre a janela da câmera sem erros.
- [ ] **7. Reconhecimento de Gestos:** Ao fazer um gesto treinado na frente da câmera, o nome do gesto e a confiança aparecem na janela.
- [ ] **8. Controle do Sistema:** A ação mapeada para o gesto (ex: "playpause") é executada corretamente no sistema operacional.

## Detalhes da Configuração (`config.json`)

Este arquivo centraliza as configurações do detector de gestos.

- `indice_camera`: `0` para a câmera padrão. Mude se tiver múltiplas câmeras.
- `confianca_deteccao`: Sensibilidade mínima (`0.0` a `1.0`) para detectar uma mão.
- `confianca_rastreamento`: Sensibilidade mínima (`0.0` a `1.0`) para rastrear a mão após a detecção inicial.
- `frames_confirmacao_gesto`: Número de frames seguidos que um gesto deve ser detectado para ser confirmado. Evita acionamentos acidentais.
- `intervalo_entre_comandos_segundos`: Tempo de espera (em segundos) antes de permitir que um novo comando seja disparado.
- `usar_modelo_gesto`: `true` para usar seu modelo treinado. `false` para desativar o reconhecimento.
- `gesto_modelo_path`: Caminho para o seu modelo `.h5`.
- `gesto_labels`: **Importante:** A ordem dos nomes dos gestos deve ser **exatamente a mesma** usada na interface web de coleta.
- `gesto_confianca_minima`: Limiar de confiança (`0.0` a `1.0`) para que um gesto seja considerado válido.
- `mapeamento_gestos`: Mapeia um nome de gesto para uma tecla ou comando do `pyautogui`. Gestos não listados aqui serão ignorados.

## Estrutura de Arquivos Essenciais

- `index.html`: Interface web para coleta de dados.
- `src/app.js`: Lógica da interface web.
- `requirements.txt`: Lista de dependências Python.
- `gesture-dataset.json`: Arquivo com suas amostras de gestos (gerado por você).
- `train_model.py`: Script para treinar o modelo de IA.
- `config.json`: Arquivo de configuração principal.
- `src/detector_gestos/main.py`: O programa principal que executa o controle por gestos.
