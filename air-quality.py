import serial, time
from Adafruit_IO import Client
from twython import Twython

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

# Send the recorded value to Adafruit IO
def sendAdafruit(): 
	data = []
	for index in range(0,10):
		datum = ser.read()
		data.append(datum)

	pmtwofive = int.from_bytes(b''.join(data[2:4]), byteorder='little') / 10
	aio.send('kingswoodtwofive', pmtwofive)
	pmten = int.from_bytes(b''.join(data[4:6]), byteorder='little') / 10
	aio.send('kingswoodten', pmten)

	return pmtwofive, pmten

# Send a new status with value of PM2.5 and PM10
def sendTweet(pm25, pm10):
    twitter.update_status(status='For now, there are ' + str(pm25) + 'µg/m3 of PM2.5 and ' + str(pm10) + 'µg/m3 of PM10')

def main():
	pm25, pm10 = sendAdafruit()
	sendTweet(pm25, pm10)

	while True:
		sendAdafruit()
		time.sleep(10)
	
if __name__ == '__main__':
    main()