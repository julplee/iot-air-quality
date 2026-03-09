import serial, time
from Adafruit_IO import Client
from twython import Twython

PROBE_WRITING_DELAY = 10

TWITTER_APP_KEY = 'YOUR_APP_KEY'
TWITTER_APP_SECRET = 'YOUR_APP_SECRET'
TWITTER_OAUTH_TOKEN = 'YOUR_OAUTH_TOKEN'
TWITTER_OAUTH_TOKEN_SECRET = 'YOUR_OAUTH_TOKEN_SECRET'

ADAFRUIT_IO_USERNAME = 'YOUR_AIO_USERNAME'
ADAFRUIT_IO_KEY = 'YOUR_AIO_KEY'

# Create an instance of the adafruit REST client.
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

# Create an instance of the Twitter client.
twitter = Twython(TWITTER_APP_KEY, TWITTER_APP_SECRET, TWITTER_OAUTH_TOKEN, TWITTER_OAUTH_TOKEN_SECRET)

# Create an instance of the serial manager of SDS011
ser = serial.Serial('/dev/ttyUSB0')

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

def takeMeasure():
	frame = read_frame()
	pm25 = int.from_bytes(frame[2:4], byteorder='little') / 10
	pm10 = int.from_bytes(frame[4:6], byteorder='little') / 10

	return pm25, pm10

# Send the recorded value to Adafruit IO
def sendAdafruit(pm25, pm10): 
	aio.send('kingswoodtwofive', pm25)
	aio.send('kingswoodten', pm10)

# Send a new status with value of PM2.5 and PM10
def sendTweet(pm25, pm10):
    twitter.update_status(status='For now, there are ' + str(pm25) + ' µg/m3 of PM2.5 and ' + str(pm10) + ' µg/m3 of PM10')

def main():
	pm25, pm10 = takeMeasure()
	sendTweet(pm25, pm10)

	while True:
		pm25, pm10 = takeMeasure()
		sendAdafruit(pm25, pm10)
		time.sleep(PROBE_WRITING_DELAY)
	
if __name__ == '__main__':
    main()
