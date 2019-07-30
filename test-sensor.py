import serial, time

# Create an instance of the serial manager of SDS011
ser = serial.Serial('/dev/ttyUSB0')

while True:
    data = []
    for index in range(0,10):
        datum = ser.read()
        data.append(datum)

    pm25 = int.from_bytes(b''.join(data[2:4]), byteorder='little') / 10
    pm10 = int.from_bytes(b''.join(data[4:6]), byteorder='little') / 10

    print(str(pm25) + ' µg/m3 of PM2.5 and ' + str(pm10) + ' µg/m3 of PM10')
    
    time.sleep(10)