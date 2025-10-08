# Projeto de Controle por Gestos com IA

Este projeto permite controlar o computador (ex: tocar e pausar músicas) através de gestos de mão customizados, treinados por você.

O fluxo de trabalho do projeto é dividido em três etapas principais:

## Fluxo de Trabalho

### 1. Coleta de Dados (Navegador Web)

- **Objetivo:** Coletar amostras dos gestos que você quer que o sistema reconheça.
- **Como fazer:**
  1. Abra o arquivo `index.html` em um navegador (usando um servidor local, ex: `python -m http.server`).
  2. Defina os nomes das suas classes de gestos (ex: `pinça, passar, neutro`).
  3. Use os controles para gravar várias amostras de cada gesto.
  4. Ao final, clique em **"Exportar Dataset"** para baixar o arquivo `gesture-dataset.json`.

### 2. Treinamento do Modelo (Python)

- **Objetivo:** Usar as amostras coletadas para treinar um modelo de Inteligência Artificial.
- **Como fazer:**
  1. Mova o arquivo `gesture-dataset.json` para a pasta raiz do projeto (`C:\projeto_IA2\`).
  2. No terminal, na pasta raiz, execute o script de treinamento:
     ```bash
     python train_model.py
     ```
  3. Este script criará o arquivo `models/meu_modelo/hand-gesture.h5`, que é o seu modelo treinado.

### 3. Execução e Controle (Python)

- **Objetivo:** Rodar o programa principal que usa a câmera para reconhecer seus gestos treinados e controlar o computador.
- **Como fazer:**
  1. Verifique o arquivo `config.json` para customizar o comportamento (ex: qual tecla do teclado associar a cada gesto, limiar de confiança, etc.).
  2. No terminal, na pasta raiz, execute o programa principal:
     ```bash
     python -m src.detector_gestos.main
     ```
  3. Uma janela com a câmera se abrirá. Agora você pode controlar outros aplicativos (Spotify, YouTube, etc.) com seus gestos.

## Estrutura de Arquivos Essenciais

- `index.html`: Interface web para coleta de dados.
- `src/app.js`: Lógica da interface web.
- `gesture-dataset.json`: Arquivo com suas amostras de gestos (gerado por você).
- `train_model.py`: Script para treinar o modelo de IA a partir do seu dataset.
- `config.json`: Arquivo de configuração principal (caminho do modelo, mapeamento de gestos, etc.).
- `src/detector_gestos/main.py`: O programa principal que executa o controle por gestos.