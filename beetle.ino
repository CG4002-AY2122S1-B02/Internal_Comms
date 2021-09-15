#include "CRC.h"

// * Constants
#define BAUD_RATE 115200
#define SAMPLING_PERIOD 20 // 20ms, so 50Hz
#define HELLO_PACKET 'H'
#define ACK_PACKET 'A'
#define DATA_PACKET 'D'
#define EMG_PACKET 'E'
#define START_DANCE_PACKET 'S'
#define TIMESTAMP 'T'

// * Time related global variables
unsigned long currentTime = 0;
unsigned long previousPacketTime = 0;

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

// ? Read data from sensors (IN THE FUTURE)
// * Generate fake accelerometer and rotational data
void readData() {
    accelX = -6000
    accelY = 13880
    accelZ = -1380
    rotX = 915
    rotY = -68
    rotZ = -49
}

// * ISN, Packet Type, Possible Data, Error Checking
void sendPacket(char packetType) {

    switch (packetType) {
        case HELLO_PACKET:
            Serial.println("Excuse me, you are not allowed to send Hello Packets!");
            break;

        case ACK_PACKET:
            Serial.write(sequenceNumber);
            Serial.write(ACK_PACKET);

            uint8_t packetSent[2] = {sequenceNumber, ACK_PACKET};
            Serial.write(calcCRC8(packetSent, 2));
            break;

        case DATA_PACKET:
            Serial.write(sequenceNumber);
            Serial.write(DATA_PACKET);
            readData();
            Serial.write()
            uint8_t packetSent[8] = {sequenceNumber,  DATA_PACKET};
            Serial.write(calcCRC8(packetSent, 8));
            break;

        case EMG_PACKET:
            break;

        case TIMESTAMP:
            break;
    }

    // Increase sequence number everytime a packet is sent out
    sequenceNumber++;
}


void setup() {
    // * Initialization
    Serial.begin(BAUD_RATE);
}

void loop() {

    if (Serial.available()) {
        byte packetType = Serial.read();

        switch (packetType) {
            case HELLO_PACKET:
                // Handshake starts from laptop. Reply handshake with ACK
                handshakeStart = true;
                handshakeEnd = false;
                sendPacket(ACK_PACKET);
                break;
            case ACK_PACKET:
                // Received last ACK from laptop. Handshake complete
                if (handshakeStart) {
                    handshakeStart = false;
                    handshakeEnd = true;
                }
                break;
            // TODO reset packet to handle random disconnections
        }
    }

    // Handshake completed
    if (handshakeEnd) {
        currentTime = millis();

        // Interval less than sampling period, do not do anything
        if (currentTime - previousPacketTime < SAMPLING_PERIOD) {
            return;
        }

        // Interval more than sampling period
        sendPacket(DATA_PACKET);
        previousPacketTime = currentTime;
    }

}