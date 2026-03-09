import serial, time

# Create an instance of the serial manager of SDS011
#ser = serial.Serial('/dev/ttyUSB0')
ser = serial.Serial('COM4')

def read_frame():
    while True:
        header = ser.read()
        if header != b'\xaa':
            continue

        frame = header + ser.read(9)
        if len(frame) != 10:
            continue

        if frame[1] != 0xC0 or frame[9] != 0xAB:
            continue

        checksum = sum(frame[2:8]) % 256
        if frame[8] != checksum:
            continue

        return frame

while True:
    frame = read_frame()
    pm25 = int.from_bytes(frame[2:4], byteorder='little') / 10
    pm10 = int.from_bytes(frame[4:6], byteorder='little') / 10

    print(str(pm25) + ' µg/m3 of PM2.5 and ' + str(pm10) + ' µg/m3 of PM10')
    
    time.sleep(10)
