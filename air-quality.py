import os
import logging
import serial, time
from Adafruit_IO import Client
from twython import Twython

PROBE_WRITING_DELAY = 10
ERROR_RETRY_DELAY = 5
SERIAL_TIMEOUT = 5

aio = None
twitter = None
logger = logging.getLogger(__name__)

# Create an instance of the serial manager of SDS011
ser = serial.Serial('/dev/ttyUSB0', timeout=SERIAL_TIMEOUT)

def require_env(name):
	value = os.getenv(name)
	if not value:
		raise RuntimeError('Missing required environment variable: ' + name)
	return value

def configure_clients():
	global aio, twitter

	adafruit_io_username = require_env('ADAFRUIT_IO_USERNAME')
	adafruit_io_key = require_env('ADAFRUIT_IO_KEY')
	twitter_app_key = require_env('TWITTER_APP_KEY')
	twitter_app_secret = require_env('TWITTER_APP_SECRET')
	twitter_oauth_token = require_env('TWITTER_OAUTH_TOKEN')
	twitter_oauth_token_secret = require_env('TWITTER_OAUTH_TOKEN_SECRET')

	# Create an instance of the adafruit REST client.
	aio = Client(adafruit_io_username, adafruit_io_key)

	# Create an instance of the Twitter client.
	twitter = Twython(
		twitter_app_key,
		twitter_app_secret,
		twitter_oauth_token,
		twitter_oauth_token_secret,
	)

def read_frame():
	while True:
		header = ser.read()
		if not header:
			raise TimeoutError('Timed out waiting for SDS011 frame header')
		if header != b'\xaa':
			continue

		frame = header + ser.read(9)
		if len(frame) != 10:
			raise TimeoutError('Timed out waiting for complete SDS011 frame')

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
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s %(levelname)s %(message)s',
	)
	configure_clients()
	try:
		pm25, pm10 = takeMeasure()
		sendTweet(pm25, pm10)
	except (TimeoutError, serial.SerialException) as exc:
		logger.exception('Failed to read SDS011 data during startup: %s', exc)
	except Exception as exc:
		logger.exception('Failed to publish startup tweet: %s', exc)

	while True:
		try:
			pm25, pm10 = takeMeasure()
			sendAdafruit(pm25, pm10)
			time.sleep(PROBE_WRITING_DELAY)
		except (TimeoutError, serial.SerialException) as exc:
			logger.exception('SDS011 read failed: %s', exc)
			time.sleep(ERROR_RETRY_DELAY)
		except Exception as exc:
			logger.exception('Failed to publish measurement: %s', exc)
			time.sleep(ERROR_RETRY_DELAY)
	
if __name__ == '__main__':
    main()
