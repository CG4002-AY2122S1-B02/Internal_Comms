# %%
# * Imports and initialization
from time import sleep
from bluepy.btle import BTLEDisconnectError, Scanner, DefaultDelegate, Peripheral
import struct


# * Different Packet Types
HELLO = 'H'
ACK = 'A'
DATA = 'D'
EMG = 'E'
START_DANCE = 'S'
TIMESTAMP = 'T'


# * Bluetooth Data
BLE_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
BLE_CHARACTERISTIC_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"


# * Mac Addresses of Bluno Beetles
BEETLE_1 = 'b0:b1:13:2d:b4:01'
BEETLE_2 = 'b0:b1:13:2d:b6:55'
BEETLE_3 = 'b0:b1:13:2d:b5:0d'
ALL_BEETLE_MAC = [BEETLE_1, BEETLE_2, BEETLE_3]


# * Handshake status of Beetles
BEETLE_HANDSHAKE_STATUS = {
    BEETLE_1: False,
    BEETLE_2: False,
    BEETLE_3: False
}


# %%

# * Delegate that is attached to each Beetle peripheral
class Delegate(DefaultDelegate):
    # TODO add buffer for fragmentation handling

    def __init__(self, mac_addr):
        DefaultDelegate.__init__(self)
        self.mac_addr = mac_addr

    # * Handles incoming packets from serial comms
    def handleNotification(self, cHandle, data):
        # TODO route relevant packets to external comms
        print("#DEBUG#: Printing Raw Data here: ", data)

        # Received ACK packet
        if (len(data) == 3):
            # ISN, 'A', CRC8
            received_packet = struct.unpack('Bcc', data)
            if (received_packet[1] == b'A'):
                BEETLE_HANDSHAKE_STATUS[self.mac_addr] = True
                print('Received ACK packet from %s' % self.mac_addr)


# TODO add other methods for BeetleSerialClass for writing to serial comms
class BeetleWrapper():
    def __init__(self, beetle_peripheral_object):
        self.beetle_periobj = beetle_peripheral_object
        self.serial_service = self.beetle_periobj.getServiceByUUID(
            BLE_SERVICE_UUID)
        self.serial_characteristic = self.serial_service.getCharacteristics()[
            0]

    # * Initiate the start of handshake sequence with Beetle
    def start_handshake(self):
        print("Starting handshake with %s" % self.beetle_periobj.addr)

        # While status is not true
        # Keep sending packet and keep track number of packets sent until response
        counter = 1
        try:
            while not BEETLE_HANDSHAKE_STATUS[self.beetle_periobj.addr]:
                # ! May throw BTLEException
                self.serial_characteristic.write(
                    bytes(HELLO, 'utf-8'), withResponse=False)
                print("%s H packets sent to Beetle %s" %
                      (counter, self.beetle_periobj.addr))

                # True if received packet from Beetle. Return ACK
                if self.beetle_periobj.waitForNotifications(3):
                    print("Successful connection with %s" %
                          self.beetle_periobj.addr)
                    # ! May throw BTLEEXcpetion
                    self.serial_characteristic.write(
                        bytes(ACK, 'utf-8'), withResponse=False)

                counter += 1
            return True

        except BTLEDisconnectError:
            print("Beetle %s disconnected. Attempt reconnection..." %
                  self.beetle_periobj.addr)
            self.reconnect()

    def reconnect(self):
        print("Attempting reconnection with %s" % self.beetle_periobj.addr)
        try:
            self.beetle_periobj.disconnect()
            sleep(5)
            self.beetle_periobj.connect()
            self.beetle_periobj.setDelegate(Delegate(self.beetle_periobj.addr))
        except Exception as e:
            print("#DEBUG#: Error reconnection")
            print(e)
            self.reconnect()


class Initialize:
    # * Returns a list of bluepy devices that match Beetle's MAC
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

    # * Devices are a list of ScanEntries that match Beetle's MAC
    # * Returns a list of created Peripherals for Beetles
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
devices = Initialize.scan()
beetle_peripherals = Initialize.create_peripherals(devices)

# ! Testing grounds
test = beetle_peripherals[0]
test_beetle_class = BeetleWrapper(test)
test_beetle_class.start_handshake()


# %%
# ? SAMPLE CODES
# for dev in devices:
#     print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
#     for (adtype, desc, value) in dev.getScanData():
#         print("  %s = %s" % (desc, value))

# scanner = Scanner().withDelegate(ScanDelegate())
