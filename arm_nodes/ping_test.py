from dynamixel_sdk import PortHandler, PacketHandler

port = PortHandler('/dev/ttyUSB0')
port.openPort()
ph = PacketHandler(2.0)

for baud in [3000000, 1000000, 57600]:
    port.setBaudRate(baud)
    for dxl_id in range(1, 10):
        model, result, err = ph.ping(port, dxl_id)
        if result == 0:
            print(f"baud={baud} ID={dxl_id} model={model}")
print("done")