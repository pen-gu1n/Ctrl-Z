from dynamixel_sdk import PortHandler, PacketHandler

port = PortHandler('/dev/ttyUSB0')
port.openPort()
port.setBaudRate(3000000)
ph = PacketHandler(2.0)

for dxl_id in range(2, 10):
    # Max Position Limit (addr 48, 4 bytes)
    v48, r48, e48 = ph.read4ByteTxRx(port, dxl_id, 48)
    # Position P Gain (addr 84, 2 bytes)
    v84, r84, e84 = ph.read2ByteTxRx(port, dxl_id, 84)
    print(f"ID={dxl_id} addr48={v48} (res={r48}) addr84={v84} (res={r84})")