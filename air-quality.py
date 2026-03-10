import os
import logging
import serial, time
from Adafruit_IO import Client
from twython import Twython
from twython.exceptions import TwythonError
from env_loader import load_local_env

try:
	import board
	import busio
	import adafruit_ssd1306
	from PIL import Image, ImageDraw, ImageFont
except ImportError:
	board = None
	busio = None
	adafruit_ssd1306 = None
	Image = None
	ImageDraw = None
	ImageFont = None

PROBE_WRITING_DELAY = 10
ERROR_RETRY_DELAY = 5
SERIAL_TIMEOUT = 5
DEFAULT_SERIAL_PORT = '/dev/ttyUSB0'
DEFAULT_PM25_FEED = 'kingswoodtwofive'
DEFAULT_PM10_FEED = 'kingswoodten'
DEFAULT_DISPLAY_WIDTH = 128
DEFAULT_DISPLAY_HEIGHT = 64
DEFAULT_DISPLAY_I2C_ADDRESS = 0x3C

load_local_env()

TWITTER_ENABLED = os.getenv('ENABLE_TWITTER', 'false').lower() == 'true'
DISPLAY_ENABLED = os.getenv('ENABLE_DISPLAY', 'true').lower() == 'true'

aio = None
twitter = None
pm25_feed = None
pm10_feed = None
display = None
display_draw = None
display_image = None
display_font = None
logger = logging.getLogger(__name__)

# Create an instance of the serial manager of SDS011
serial_port = os.getenv('SDS011_SERIAL_PORT', DEFAULT_SERIAL_PORT)
ser = serial.Serial(serial_port, timeout=SERIAL_TIMEOUT)

def require_env(name):
	value = os.getenv(name)
	if not value:
		raise RuntimeError('Missing required environment variable: ' + name)
	return value

def configure_clients():
	global aio, twitter, pm25_feed, pm10_feed

	adafruit_io_username = require_env('ADAFRUIT_IO_USERNAME')
	adafruit_io_key = require_env('ADAFRUIT_IO_KEY')
	pm25_feed = os.getenv('ADAFRUIT_IO_PM25_FEED', DEFAULT_PM25_FEED)
	pm10_feed = os.getenv('ADAFRUIT_IO_PM10_FEED', DEFAULT_PM10_FEED)

	# Create an instance of the adafruit REST client.
	aio = Client(adafruit_io_username, adafruit_io_key)

	if not TWITTER_ENABLED:
		logger.info('Twitter posting disabled; set ENABLE_TWITTER=true to enable startup tweets.')
		return

	twitter_app_key = require_env('TWITTER_APP_KEY')
	twitter_app_secret = require_env('TWITTER_APP_SECRET')
	twitter_oauth_token = require_env('TWITTER_OAUTH_TOKEN')
	twitter_oauth_token_secret = require_env('TWITTER_OAUTH_TOKEN_SECRET')

	# Create an instance of the Twitter client.
	twitter = Twython(
		twitter_app_key,
		twitter_app_secret,
		twitter_oauth_token,
		twitter_oauth_token_secret,
	)

def configure_display():
	global display, display_draw, display_image, display_font

	if not DISPLAY_ENABLED:
		logger.info('Display disabled; set ENABLE_DISPLAY=true to enable SSD1306 output.')
		return

	if not all([board, busio, adafruit_ssd1306, Image, ImageDraw, ImageFont]):
		logger.warning('SSD1306 display libraries are unavailable; continuing without display output.')
		return

	try:
		width = int(os.getenv('DISPLAY_WIDTH', DEFAULT_DISPLAY_WIDTH))
		height = int(os.getenv('DISPLAY_HEIGHT', DEFAULT_DISPLAY_HEIGHT))
		address = int(os.getenv('DISPLAY_I2C_ADDRESS', hex(DEFAULT_DISPLAY_I2C_ADDRESS)), 0)
		i2c = busio.I2C(board.SCL, board.SDA)
		display = adafruit_ssd1306.SSD1306_I2C(width, height, i2c, addr=address)
		display_image = Image.new('1', (display.width, display.height))
		display_draw = ImageDraw.Draw(display_image)
		display_font = ImageFont.load_default()
		display.fill(0)
		display.show()
		write_display('Air quality', 'Starting...', '')
	except Exception as exc:
		display = None
		display_draw = None
		display_image = None
		display_font = None
		logger.exception('Failed to initialize SSD1306 display: %s', exc)

def write_display(line1, line2='', line3=''):
	if display is None or display_draw is None or display_image is None or display_font is None:
		return

	display_draw.rectangle((0, 0, display.width, display.height), outline=0, fill=0)
	display_draw.text((0, 0), str(line1), font=display_font, fill=255)
	display_draw.text((0, 16), str(line2), font=display_font, fill=255)
	display_draw.text((0, 32), str(line3), font=display_font, fill=255)
	display.image(display_image)
	display.show()

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
	aio.send(pm25_feed, pm25)
	aio.send(pm10_feed, pm10)

# Send a new status with value of PM2.5 and PM10
def sendTweet(pm25, pm10):
    if twitter is None:
        return
    twitter.update_status(status='For now, there are ' + str(pm25) + ' µg/m3 of PM2.5 and ' + str(pm10) + ' µg/m3 of PM10')

def main():
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s %(levelname)s %(message)s',
	)
	configure_clients()
	configure_display()
	try:
		pm25, pm10 = takeMeasure()
		write_display('Air quality', 'PM2.5: ' + str(pm25), 'PM10 : ' + str(pm10))
		sendTweet(pm25, pm10)
	except (TimeoutError, serial.SerialException) as exc:
		write_display('Air quality', 'Sensor error', 'Retrying...')
		logger.exception('Failed to read SDS011 data during startup: %s', exc)
	except TwythonError as exc:
		logger.error('Startup tweet failed: %s', exc)
	except Exception as exc:
		write_display('Air quality', 'Startup error', 'See logs')
		logger.exception('Failed to publish startup tweet: %s', exc)

	while True:
		try:
			pm25, pm10 = takeMeasure()
			write_display('Air quality', 'PM2.5: ' + str(pm25), 'PM10 : ' + str(pm10))
			sendAdafruit(pm25, pm10)
			time.sleep(PROBE_WRITING_DELAY)
		except (TimeoutError, serial.SerialException) as exc:
			write_display('Air quality', 'Sensor error', 'Retrying...')
			logger.exception('SDS011 read failed: %s', exc)
			time.sleep(ERROR_RETRY_DELAY)
		except Exception as exc:
			write_display('Air quality', 'Publish error', 'See logs')
			logger.exception('Failed to publish measurement: %s', exc)
			time.sleep(ERROR_RETRY_DELAY)
	
if __name__ == '__main__':
    main()
