#include "CRC.h"

// * Constants
#define BAUD_RATE 115200
#define SAMPLING_PERIOD 100 // 20ms, so 50Hz
#define EMG_SAMPLING_PERIOD 10 // 10ms, so 100Hz
#define HELLO_PACKET 'H'
#define ACK_PACKET 'A'
#define RESET_PACKET 'R'
#define DATA_PACKET 'D'
#define EMG_PACKET 'E'
#define START_DANCE_PACKET 'S' // TODO yet to be implemented
#define TIMESTAMP 'T' // TODO yet to be implemented

// * Time related global variables
unsigned long currentTime = 0;
unsigned long previousPacketTime = 0;
unsigned long previousEMGPacketTime = 0;

unsigned int sequenceNumber = 0;

// * Handshake status
bool handshakeStart = false;
bool handshakeEnd = false;

// * Data related global variables
int16_t accelX;
int16_t accelY;
int16_t accelZ;
int16_t rotX;
int16_t rotY;
int16_t rotZ;

int16_t emgData;

// *   ______ _    _ _   _  _____
// *  |  ____| |  | | \ | |/ ____|
// *  | |__  | |  | |  \| | |
// *  |  __| | |  | | . ` | |
// *  | |    | |__| | |\  | |____
// *  |_|     \____/|_| \_|\_____|

// * Calculate CRC8 for checksum
uint8_t calcCRC8(uint8_t *data, int len) {
    return crc8(data, len);
}

// * Reset Beetle Programmatically
void (* resetBeetle) (void) = 0;

// ? Read data from sensors (IN THE FUTURE)
// * Generate fake accelerometer and rotational data
void readData() {
    // TODO random generation of data
    accelX = -6000;
    accelY = 13880;
    accelZ = -1380;
    rotX = 915;
    rotY = -68;
    rotZ = -49;
}

// ? Read data from EMG sensors (IN THE FUTURE)
// * Generate fake EMG data
void readEMGData() {
    // TODO random generation of data
    emgData = 200;
}

// * Total 4 bytes currently
void sendACKPacket(char packetType) {

    Serial.write(sequenceNumber); // Two bytes SN
    Serial.write(ACK_PACKET); // One byte packet type

    uint8_t packetSent[2] = {sequenceNumber, ACK_PACKET};
    Serial.write(calcCRC8(packetSent, 2)); // One byte checksum

    // Increase sequence number everytime a packet is sent out
    sequenceNumber++;
}

// * Total 20 bytes currently (max)
void sendDataPacket() {

    Serial.write(sequenceNumber); // Two bytes SN
    Serial.write(DATA_PACKET); // One byte packet type

    // ! Remember to change this to actual reading of sensors data in the future
    readData();

    // 6 bytes accelerometer, 6 bytes rotational
    Serial.write(accelX);
    Serial.write(accelY);
    Serial.write(accelZ);
    Serial.write(rotX);
    Serial.write(rotY);
    Serial.write(rotZ);

    // TODO add in sending of timestamp

    uint8_t dataPacketSent[8] = {sequenceNumber, accelX, accelY, accelZ, rotX, rotY, rotZ, DATA_PACKET};
    Serial.write(calcCRC8(dataPacketSent, 8)); // One byte checksum
}

// * Total 6 bytes
void sendEMGPacket() {

    Serial.write(sequenceNumber); // Two bytes SN
    Serial.write(EMG_PACKET); // One byte packet type

    // ! Remember to change this to actual reading in the future
    readEMGData();

    // 2 bytes EMG data
    Serial.write(emgData);

    uint8_t emgPacketSent[3] = {sequenceNumber, EMG_PACKET, emgData};
    Serial.write(calcCRC8(emgPacketSent, 3)); // One byte checksum
}

// * Initialization
void setup() {

    Serial.begin(BAUD_RATE);

    // ? Is this needed?
    currentTime = 0;
    previousPacketTime = 0;
    previousEMGPacketTime = 0;
}

void loop() {
    if (Serial.available()) {
        byte packetType = Serial.read();

        switch (packetType) {
            case HELLO_PACKET:
                // Handshake starts from laptop. Reply handshake with ACK
                handshakeStart = true;
                handshakeEnd = false;
                sendACKPacket(ACK_PACKET);
                break;
            case ACK_PACKET:
                // Received last ACK from laptop. Handshake complete
                if (handshakeStart) {
                    handshakeStart = false;
                    handshakeEnd = true;
                    previousPacketTime = 0;
                    currentTime = 0;
                }
                break;
            case RESET_PACKET:
                resetBeetle();
                break;
        }
    }

    // Handshake completed
    if (handshakeEnd) {
        currentTime = millis();

        // Send EMG Packet Data
        if (currentTime - previousEMGPacketTime > EMG_SAMPLING_PERIOD) {
            readEMGData();
            sendEMGPacket();
            previousEMGPacketTime = currentTime;
        }

        // Send sensor data
        if (currentTime - previousPacketTime > SAMPLING_PERIOD) {
            readData();
            sendDataPacket();
            previousPacketTime = currentTime;
        }

    }

}