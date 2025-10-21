#include <BleKeyboard.h>
#include <Arduino.h>

BleKeyboard bleKeyboard("Controle de Gestos IA", "GIA", 100);
const long SERIAL_BAUDRATE = 115200;

const byte MAX_COMMAND_SIZE = 32;
char receivedChars[MAX_COMMAND_SIZE];
bool newData = false;

void receiveSerialData() {
    static byte index = 0;
    const char endMarker = '\n';
    char rc;

    while (Serial.available() > 0 && !newData) {
        rc = Serial.read();

        if (rc != endMarker) {
            if (index < MAX_COMMAND_SIZE - 1) {
                receivedChars[index] = rc;
                index++;
            }
        } else {
            receivedChars[index] = '\0';
            index = 0;
            newData = true;
        }
    }
}

void processCommand() {
    String command = String(receivedChars);
    command.trim();

    Serial.print("Comando: '");
    Serial.print(command);
    Serial.println("'");

    if (command == "playpause") {
        bleKeyboard.write(KEY_MEDIA_PLAY_PAUSE);
    } else if (command == "nexttrack") {
        bleKeyboard.write(KEY_MEDIA_NEXT_TRACK);
    } else if (command == "prevtrack") {
        bleKeyboard.write(KEY_MEDIA_PREVIOUS_TRACK);
    }
}

void setup() {
    Serial.begin(SERIAL_BAUDRATE);
    Serial.println("Controlador de Gestos (Alta Performance) iniciado.");
    bleKeyboard.begin();
    Serial.println("Bluetooth iniciado. Aguardando comandos...");
}

void loop() {
    if (bleKeyboard.isConnected()) {
        receiveSerialData();

        if (newData) {
            processCommand();
            newData = false;
        }
    } else {
        static unsigned long lastMsgTime = 0;
        if (millis() - lastMsgTime > 2000) {
            Serial.println("Aguardando conexão do celular...");
            lastMsgTime = millis();
        }
    }
}
