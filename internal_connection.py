# %%
# * Imports and initialization
from time import sleep
from bluepy.btle import BTLEDisconnectError, Scanner, DefaultDelegate, Peripheral
import struct
from crccheck.crc import Crc8
import threading


# * Different Packet Types
HELLO = 'H'
ACK = 'A'
RESET = 'R'
DATA = 'D'
EMG = 'E'
START_DANCE = 'S'
TIMESTAMP = 'T'


# * Bluetooth Data
BLE_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
BLE_CHARACTERISTIC_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"


# * Mac Addresses of Bluno Beetles
# BEETLE_1 = 'b0:b1:13:2d:b4:01'
# BEETLE_2 = 'b0:b1:13:2d:b6:55'
# BEETLE_3 = 'b0:b1:13:2d:b5:0d'
TEMP_BEETLE = 'b0:b1:13:2d:d4:ca'
ALL_BEETLE_MAC = [TEMP_BEETLE]


# * Handshake status of Beetles
BEETLE_HANDSHAKE_STATUS = {
    # BEETLE_1: False,
    # BEETLE_2: False,
    # BEETLE_3: False,
    TEMP_BEETLE: False
}

# * Requesting Reset status of Beetles
BEETLE_REQUEST_RESET_STATUS = {
    # BEETLE_1: False,
    # BEETLE_2: False,
    # BEETLE_3: False,
    TEMP_BEETLE: False
}

# * Sequence number of Beetles
BEETLE_SEQUENCE_NUMBER = {
    # BEETLE_1: 0,
    # BEETLE_2: 0,
    # BEETLE_3: 0,
    TEMP_BEETLE: 0
}


# %%

# * Delegate that is attached to each Beetle peripheral
class Delegate(DefaultDelegate):

    def __init__(self, mac_addr):
        DefaultDelegate.__init__(self)
        self.mac_addr = mac_addr
        self.buffer = b''

    # * Handles incoming packets from serial comms
    def handleNotification(self, cHandle, data):
        # print("#DEBUG#: Printing Raw Data here: %s. Length: %s" % (data, len(data)))

        # Handshake completed. Handle data packets
        if (BEETLE_HANDSHAKE_STATUS[self.mac_addr]):
            self.buffer += data

            # Check received sequence number matches current sequence number
            # Based on what is the packet type, retrieve specific number of bytes

            decodedSequenceNumber = struct.unpack('!H', self.buffer[0:2])
            if (decodedSequenceNumber[0] == BEETLE_SEQUENCE_NUMBER[self.mac_addr]):
                
                # Received EMG Packet 6 bytes
                if (self.buffer[2] == 69 and len(self.buffer) > 6): # * ASCII Code E (EMG)
                    raw_packet_data = self.buffer[0: 6]
                    parsed_packet_data = struct.unpack('!Hchc', raw_packet_data)

                    if not self.checkCRC(5):
                        print("#DEBUG#: CRC Checksum doesn't match for %s. Resetting..." % self.mac_addr)
                        BEETLE_REQUEST_RESET_STATUS[self.mac_addr] = True
                        return

                    self.sendDataToUltra96(parsed_packet_data)
                    self.buffer = self.buffer[6:]
                    BEETLE_SEQUENCE_NUMBER[self.mac_addr] += 1
    

                # Received Data Packet 16 bytes
                elif (self.buffer[2] == 68 and len(self.buffer) > 16): # * ASCII Code D (DATA)
                    raw_packet_data = self.buffer[0: 16]
                    parsed_packet_data = struct.unpack('!Hchhhhhhc', raw_packet_data)

                    if not self.checkCRC(15):
                        print("#DEBUG#: CRC Checksum doesn't match for %s. Resetting..." % self.mac_addr)
                        BEETLE_REQUEST_RESET_STATUS[self.mac_addr] = True
                        return

                    self.sendDataToUltra96(parsed_packet_data)
                    self.buffer = self.buffer[16:]
                    BEETLE_SEQUENCE_NUMBER[self.mac_addr] += 1


                # Received Timestamp packet 8 bytes
                elif (self.buffer[2] == 84 and len(self.buffer) > 8): # * ASCII Code T
                    raw_packet_data = self.buffer[0: 8]
                    parsed_packet_data = struct.unpack('!HcLc', raw_packet_data)

                    if not self.checkCRC(7):
                        print("#DEBUG#: CRC Checksum doesn't match for %s. Resetting..." % self.mac_addr)
                        BEETLE_REQUEST_RESET_STATUS[self.mac_addr] = True
                        return

                    self.sendDataToUltra96(parsed_packet_data)
                    self.buffer = self.buffer[8:]
                    BEETLE_SEQUENCE_NUMBER[self.mac_addr] += 1
                
            else:
                # Sequence number and received packets are out of sync
                # Request for reset by turning on a flag
                BEETLE_REQUEST_RESET_STATUS[self.mac_addr] = True


        # Received ACK packet
        elif (len(data) == 4):
            # ISN, 'A', CRC8
            received_packet = struct.unpack('!Hcc', data)
            if (received_packet[1] == b'A' and received_packet[0] == BEETLE_SEQUENCE_NUMBER[self.mac_addr]):
                BEETLE_HANDSHAKE_STATUS[self.mac_addr] = True
                BEETLE_SEQUENCE_NUMBER[self.mac_addr] += 1
                # print('#DEBUG#: Received ACK packet from %s' % self.mac_addr)

    # * Checks checksum by indicating the length of packet used to calculate checksum
    def checkCRC(self, length):
        calcChecksum = Crc8.calc(self.buffer[0: length])
        # print("#DEBUG#: Calculated checksum: %s vs Received: %s" % (calcChecksum, self.buffer[length]))
        return calcChecksum == self.buffer[length]

    # TODO Change this to external comms code in the future
    def sendDataToUltra96(self, data):
        print(data)


class BeetleThread(threading.Thread):
    def __init__(self, beetle_peripheral_object):
        threading.Thread.__init__(self)

        self.beetle_periobj = beetle_peripheral_object
        self.serial_service = self.beetle_periobj.getServiceByUUID(
            BLE_SERVICE_UUID)
        self.serial_characteristic = self.serial_service.getCharacteristics()[
            0]

    def run(self):
        self.start_handshake()
        self.listenIn()

    # * Initiate the start of handshake sequence with Beetle
    def start_handshake(self):
        print("Starting handshake with %s" % self.beetle_periobj.addr)

        # While status is not true
        # Keep sending packet and keep track number of packets sent until response
        counter = 1
        try:
            while not BEETLE_HANDSHAKE_STATUS[self.beetle_periobj.addr]:
                # May throw BTLEException
                self.serial_characteristic.write(
                    bytes(HELLO, 'utf-8'), withResponse=False)
                print("%s H packets sent to Beetle %s" %
                      (counter, self.beetle_periobj.addr))

                # May be a case of fault handshake.
                # Beetle think handshake has completed but laptop doesn't
                if counter % 30 == 0:
                    print("Too many H packets sent. Arduino may be out of state. Resetting Beetle")
                    self.reset()

                # True if received packet from Beetle. Return ACK
                if self.beetle_periobj.waitForNotifications(3):
                    print("Successful connection with %s" %
                          self.beetle_periobj.addr)
                    # May throw BTLEEXcpetion
                    self.serial_characteristic.write(
                        bytes(ACK, 'utf-8'), withResponse=False)

                counter += 1
            return True

        except BTLEDisconnectError:
            print("Beetle %s disconnected. Attempt reconnection..." %
                  self.beetle_periobj.addr)
            self.reconnect()
            self.start_handshake()

    def reconnect(self):
        print("Attempting reconnection with %s" % self.beetle_periobj.addr)
        try:
            self.beetle_periobj.disconnect()
            sleep(2)
            self.beetle_periobj.connect(self.beetle_periobj.addr)
            self.beetle_periobj.withDelegate(Delegate(self.beetle_periobj.addr))
            print("Reconnection successful with %s" % self.beetle_periobj.addr)
        except Exception as e:
            print("#DEBUG#: Error reconnecting. Reason: %s" % e)
            self.reconnect()

    def reset(self):
        self.serial_characteristic.write(bytes(RESET, 'utf-8'), withResponse = False)
        print("Resetting Beetle %s" % self.beetle_periobj.addr)
        BEETLE_SEQUENCE_NUMBER[self.beetle_periobj.addr] = 0
        BEETLE_HANDSHAKE_STATUS[self.beetle_periobj.addr] = False
        BEETLE_REQUEST_RESET_STATUS[self.beetle_periobj.addr] = False
        self.reconnect()

    # * Continues watching the Beetle and check request reset flag
    # * If request reset is true, reset Beetle and reinitiate handshake
    def listenIn(self):
        try:
            while True:
                if self.beetle_periobj.waitForNotifications(3) and not BEETLE_REQUEST_RESET_STATUS[self.beetle_periobj.addr]:
                    continue;

                # If sequence number is messed up, break and reset
                if BEETLE_REQUEST_RESET_STATUS[self.beetle_periobj.addr]:
                    break;
            self.reset()
            self.start_handshake()
            self.listenIn()
        except Exception as e:
            print("#DEBUG#: Disconnection! Reason: %s" % e)
            self.reconnect()
            self.reset()
            self.start_handshake()
            self.listenIn()


class Initialize:

    # * Utilize MAC address of Beetles and directly create connection with them
    def start_peripherals():
        created_beetle_peripherals = []
        for mac in ALL_BEETLE_MAC:
            try:
                # May throw BETLEException
                print("#DEBUG# Attempting connection to %s" % mac)
                beetle = Peripheral(mac)
            except Exception as e:
                print(
                    "#DEBUG#: Failed to create peripheral for %s. Exception: %s" % (mac, e))
                continue
            
            beetle.withDelegate(Delegate(mac))
            created_beetle_peripherals.append(beetle)
        return created_beetle_peripherals

    # ! DEPRE this was only used for testing
    # Returns a list of bluepy devices that match Beetle's MAC
    def scan():
        # Initialize scanner to hci0 interface (ensure this interface is bluetooth)
        scanner = Scanner(0)
        devices = scanner.scan(5)
        found_beetles = []
        for device in devices:
            if device.addr in ALL_BEETLE_MAC:
                found_beetles.append(device)
        print('#DEBUG#: %s Beetle found!' % (len(found_beetles)))
        return found_beetles

    # ! DEPRE this was only used for testing
    # Devices are a list of ScanEntries that match Beetle's MAC
    # Returns a list of created Peripherals for Beetles
    def create_peripherals(devices):
        created_beetle_peripherals = []
        for dev in devices:
            try:
                # May throw BTLEException
                beetle = Peripheral(dev.addr)
            except:
                print(
                    "#DEBUG#: Failed to create peripheral for %s. Retrying..." % dev.addr)
                sleep(1)
                beetle = Peripheral(dev.addr)

            beetle.setDelegate(Delegate(dev.addr))
            created_beetle_peripherals.append(beetle)
        return created_beetle_peripherals


# %%
# ! Testing Grounds 
# beetle_peripherals = Initialize.start_peripherals()

# test = beetle_peripherals[0]
# test_beetle_class = BeetleThread(test)

# test_beetle_class.start_handshake()

# test_beetle_class.listenIn()

# %% 
# ! Actual main code
if __name__ == '__main__':
    beetle_peripherals = Initialize.start_peripherals()
    for found_beetle in beetle_peripherals:
        BeetleThread(found_beetle).start()
