#include "CRC.h"

// * Constants
#define BAUD_RATE 115200
#define HELLO_PACKET 'H'
#define ACK_PACKET 'A'
#define DATA_PACKET 'D'
#define EMG_PACKET 'E'
#define START_DANCE_PACKET 'S'
#define TIMESTAMP 'T'

unsigned long startTime;

unsigned int sequenceNumber = 0;

// Handshake status
bool handshakeStart = false;
bool handshakeEnd = false;

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
                startTime = millis();
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
        }
    }
}