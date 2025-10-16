# AI Gesture Media Control with ESP32

This project allows you to control media playback (play/pause, next/previous) on any Bluetooth-enabled device (like a smartphone, tablet, or smart TV) using hand gestures captured by a webcam.

The system uses artificial intelligence to recognize gestures and an ESP32 microcontroller to send the commands as if it were a Bluetooth keyboard, making it universally compatible.

<!-- Add a demonstration GIF here -->
<!-- ![Project Demonstration](path/to/your/gif.gif) -->

---

## ➤ Overview

The project combines computer vision and hardware to create an intuitive media controller. It is ideal for situations where physical access to the media device is inconvenient, such as during exercise, cooking, or when the device is far away.

### How It Works

The system architecture follows this flow:

`Webcam` → `Python (OpenCV)` → `AI Recognition (TensorFlow)` → `Command via Serial Port` → `ESP32` → `Command via Bluetooth` → `Target Device (Phone, etc.)`

### Features

- **Real-Time Gesture Recognition:** Uses MediaPipe and TensorFlow/Keras for high accuracy.
- **Universal Bluetooth Control:** The ESP32 acts as a BLE media keyboard, compatible with Android, iOS, Windows, macOS, etc.
- **Command-Line Interface:** Simple and direct execution with visual feedback through an OpenCV window.
- **Complete Training System:** Includes a web interface to collect data for new gestures and scripts to train your own AI model.

---

## ✔ Requirements

Before you begin, ensure you have the following items.

### Hardware

- **Webcam:** Any standard webcam connected to your computer.
- **ESP32 Microcontroller:** A development board like the NodeMCU-32S or similar.

### Software

- **Python 3.8+:** [Download link](https://www.python.org/downloads/).
- **Arduino IDE:** [Download link](https://www.arduino.cc/en/software).
- **Git:** (Optional, but recommended for cloning the project) [Download link](https://git-scm.com/downloads).

---

## ⚙️ SETUP: Installation and Configuration

Follow these 5 steps to prepare the entire environment.

### Step 1: Get the Project

Clone this repository to your computer using Git:

```sh
git clone <REPOSITORY_URL>
```

Or download the ZIP file and extract it.

### Step 2: Configure the Python Environment (Recommended)

To avoid package conflicts, it is highly recommended to use a virtual environment.

1.  **Open a terminal** in the project's root folder.
2.  **Create the virtual environment** (you only need to do this once):
    ```sh
    python -m venv .venv
    ```
3.  **Activate the virtual environment** (you need to do this every time you use the project):
    ```sh
    # On Windows (PowerShell/CMD)
    .\.venv\Scripts\activate
    ```
    *You will know it worked when you see `(.venv)` at the beginning of your terminal prompt.*

### Step 3: Install Dependencies

With the virtual environment active, install all necessary Python libraries:

```sh
pip install -r requirements.txt
```

### Step 4: Prepare the ESP32

1.  **Open the Arduino IDE**.
2.  **Install the Library:** Go to `Tools > Manage Libraries...` and search for and install the `BleKeyboard` library by T-vK.
3.  **Load the Sketch:** Open the `esp32_sketch/esp32_controller.ino` file in the Arduino IDE.
4.  **Upload:** Connect your ESP32 to the computer, select the correct board (`ESP32 Dev Module` or similar) and COM port in `Tools`, and click the Upload button (right arrow).

### Step 5: Pair Bluetooth

1.  With the ESP32 powered on, take your media device (phone, tablet, etc.).
2.  Scan for new Bluetooth devices.
3.  Pair with the device named **"Controle de Gestos IA"**.

---

## ▶️ USAGE: Running the Application

With the setup complete, follow the steps below to use the gesture control.

1.  **Connect the ESP32** to the computer (so the serial port is recognized).
2.  **Activate the Virtual Environment** (if not already active):
    ```sh
    .\.venv\Scripts\activate
    ```
3.  **Configure the Serial Port**:
    - Open the `config.json` file.
    - Find the `"serial_port"` key and change the value to the COM port your ESP32 is using (e.g., `"COM3"`, `"COM5"`, etc.).
    - Ensure `"usar_serial"` is set to `true`.
4.  **Run the Main Program**:
    In the terminal (with the environment active), execute:
    ```sh
    python -m src.detector_gestos.main
    ```
5.  A window with your camera's image will open, and gesture recognition will begin.

---

## 🧠 ADVANCED: Training Your Own Models

If you want to add new gestures or voice commands, follow the phases below.

### Phase 1: Data Collection and Quick Test (Browser)

Use the web interface to collect samples and train a temporary model for immediate feedback.

1.  **Start the Web Interface:**
    - In the terminal, at the project root, start a local server: `python -m http.server`.
    - Open your browser and go to: `http://localhost:8000`.

2.  **On the page, follow the instructions to:**
    - Define the names of your gestures or keywords.
    - Record several samples for each.
    - Train a quick test model.
    - Test in real-time in the browser.

3.  **Export Data for Final Training:**
    - Use the **"Export Dataset"** buttons to save the `gesture-dataset.json` and `kws-samples.json` files to the **project root folder**.

### Phase 2: Final Model Training (Terminal)

Use the Python scripts to create the `.h5` models that the main application uses.

1.  **Train the Gesture Model:**
    - Ensure `gesture-dataset.json` is in the project root.
    - In the terminal (with the virtual environment active), run:
      ```sh
      python treinamento\train_model.py
      ```

2.  **Train the Voice Model (KWS):**
    - Ensure `kws-samples.json` is in the project root.
    - In the terminal, run:
      ```sh
      python treinamento\train_kws_model.py
      ```
Both scripts will save the final models in the `models/` folder.

### Phase 3: Update Configuration

1.  Open the `config.json` file.
2.  Update the `"gesto_labels"` and `"kws_labels"` lists with the exact names of your new gestures/words.
3.  Update the `"mapeamento_gestos"` and `"mapeamento_kws"` mappings to associate each class with a command (`"playpause"`, `"nexttrack"`, etc.).

---

## ❓ Troubleshooting

- **Error: "CRITICAL ERROR connecting to serial port..."**
  - **Solution:** Check if the ESP32 is connected to the computer. Confirm that the COM port in `config.json` is the same as the one shown in the Arduino IDE. On Windows, you can find it in the "Device Manager".

- **Error: "Could not open camera..."**
  - **Solution:** Check if the webcam is connected and working. If you have more than one camera, change the `"indice_camera"` value in `config.json` (try 0, 1, 2, etc.).

- **Gestures are not recognized accurately:**
  - **Solution 1:** The ambient lighting greatly affects detection. Try a better-lit location.
  - **Solution 2:** The minimum confidence might be too high. Try lowering the `"gesto_confianca_minima"` value in `config.json`.
  - **Solution 3:** Train your own model with more samples and under varied lighting conditions for greater robustness.

---

## 🤝 Contributions

Contributions are welcome! Feel free to open an *issue* to report bugs or suggest improvements.
