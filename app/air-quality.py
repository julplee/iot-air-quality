import os
import logging
import json
import serial, time
from urllib import error, request
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
DEFAULT_DISPLAY_FONT_SIZE = 14
DEFAULT_API_TIMEOUT = 5

PM25_BREAKPOINTS = [
	(9.0, 'GOOD', 0),
	(35.4, 'MOD', 1),
	(55.4, 'USG', 2),
	(125.4, 'UNH', 3),
	(225.4, 'VUNH', 4),
	(float('inf'), 'HAZ', 5),
]

PM10_BREAKPOINTS = [
	(54.0, 'GOOD', 0),
	(154.0, 'MOD', 1),
	(254.0, 'USG', 2),
	(354.0, 'UNH', 3),
	(424.0, 'VUNH', 4),
	(float('inf'), 'HAZ', 5),
]

SEVERITY_LABELS = ['GOOD', 'MODERATE', 'SENSITIVE', 'UNHEALTHY', 'VERY UNH', 'HAZARDOUS']

load_local_env()

TWITTER_ENABLED = os.getenv('ENABLE_TWITTER', 'false').lower() == 'true'
DISPLAY_ENABLED = os.getenv('ENABLE_DISPLAY', 'true').lower() == 'true'

aio = None
twitter = None
pm25_feed = None
pm10_feed = None
api_base_url = None
api_timeout = DEFAULT_API_TIMEOUT
display = None
display_draw = None
display_image = None
display_font = None
logger = logging.getLogger(__name__)

serial_port = os.getenv('SDS011_SERIAL_PORT', DEFAULT_SERIAL_PORT)
ser = None

def require_env(name):
	value = os.getenv(name)
	if not value:
		raise RuntimeError('Missing required environment variable: ' + name)
	return value

def configure_clients():
	global aio, twitter, pm25_feed, pm10_feed, api_base_url, api_timeout

	adafruit_io_username = require_env('ADAFRUIT_IO_USERNAME')
	adafruit_io_key = require_env('ADAFRUIT_IO_KEY')
	pm25_feed = os.getenv('ADAFRUIT_IO_PM25_FEED', DEFAULT_PM25_FEED)
	pm10_feed = os.getenv('ADAFRUIT_IO_PM10_FEED', DEFAULT_PM10_FEED)
	api_base_url = os.getenv('API_BASE_URL', '').rstrip('/')
	api_timeout = float(os.getenv('API_TIMEOUT_SECONDS', DEFAULT_API_TIMEOUT))

	# Create an instance of the adafruit REST client.
	aio = Client(adafruit_io_username, adafruit_io_key)

	if api_base_url:
		logger.info('API publishing enabled for %s', api_base_url)
	else:
		logger.info('API publishing disabled; set API_BASE_URL to enable Go API uploads.')

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
		display_font = load_display_font()
		display.fill(0)
		display.show()
		write_display('Air quality', 'Starting...', '')
	except Exception as exc:
		display = None
		display_draw = None
		display_image = None
		display_font = None
		logger.exception('Failed to initialize SSD1306 display: %s', exc)

def load_display_font():
	font_size = int(os.getenv('DISPLAY_FONT_SIZE', DEFAULT_DISPLAY_FONT_SIZE))
	font_path = os.getenv('DISPLAY_FONT_PATH')

	candidate_paths = []
	if font_path:
		candidate_paths.append(font_path)

	candidate_paths.extend([
		'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
		'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
		'/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf',
	])

	for candidate in candidate_paths:
		try:
			return ImageFont.truetype(candidate, font_size)
		except OSError:
			continue

	logger.warning(
		'Falling back to PIL default font; set DISPLAY_FONT_PATH to a .ttf for a more readable display.'
	)
	return ImageFont.load_default()

def classify_particulate(value, breakpoints):
	for upper_bound, label, severity in breakpoints:
		if value <= upper_bound:
			return label, severity

	return breakpoints[-1][1], breakpoints[-1][2]

def format_particulate(value):
	return f'{value:.1f}'

def initialize_serial():
	global ser

	if ser is not None and ser.is_open:
		return ser

	if ser is not None:
		try:
			ser.close()
		except Exception:
			pass

	logger.info('Opening SDS011 serial port %s', serial_port)
	ser = serial.Serial(serial_port, timeout=SERIAL_TIMEOUT)
	return ser

def write_display(line1, line2='', line3=''):
	if display is None or display_draw is None or display_image is None or display_font is None:
		return

	display_draw.rectangle((0, 0, display.width, display.height), outline=0, fill=0)
	font_bbox = display_font.getbbox('Ag')
	line_height = max((font_bbox[3] - font_bbox[1]) + 2, 12)
	display_draw.text((0, 0), str(line1), font=display_font, fill=255)
	display_draw.text((0, line_height), str(line2), font=display_font, fill=255)
	display_draw.text((0, line_height * 2), str(line3), font=display_font, fill=255)
	display.image(display_image)
	display.show()

def write_measurement_display(pm25, pm10):
	if display is None or display_draw is None or display_image is None or display_font is None:
		return

	pm25_label, pm25_severity = classify_particulate(pm25, PM25_BREAKPOINTS)
	pm10_label, pm10_severity = classify_particulate(pm10, PM10_BREAKPOINTS)
	overall_severity = max(pm25_severity, pm10_severity)
	overall_label = SEVERITY_LABELS[overall_severity]
	font_bbox = display_font.getbbox('Ag')
	line_height = max((font_bbox[3] - font_bbox[1]) + 2, 12)
	top_fill = 255 if overall_severity >= 2 else 0
	top_text_fill = 0 if overall_severity >= 2 else 255

	display_draw.rectangle((0, 0, display.width, display.height), outline=0, fill=0)
	display_draw.rectangle((0, 0, display.width, line_height), outline=top_fill, fill=top_fill)
	display_draw.text((0, 0), overall_label[:12], font=display_font, fill=top_text_fill)
	display_draw.text((0, line_height), 'P25 ' + format_particulate(pm25) + ' ' + pm25_label, font=display_font, fill=255)
	display_draw.text((0, line_height * 2), 'P10 ' + format_particulate(pm10) + ' ' + pm10_label, font=display_font, fill=255)
	display.image(display_image)
	display.show()

def read_frame():
	initialize_serial()

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

def post_api_metric(metric_name, value):
	if not api_base_url:
		return

	endpoint = api_base_url + '/' + metric_name
	body = json.dumps({'value': value}).encode('utf-8')
	req = request.Request(
		endpoint,
		data=body,
		headers={'Content-Type': 'application/json'},
		method='POST',
	)

	with request.urlopen(req, timeout=api_timeout) as response:
		if response.status < 200 or response.status >= 300:
			raise RuntimeError('API returned HTTP ' + str(response.status) + ' for ' + metric_name)

def sendAPI(pm25, pm10):
	post_api_metric('pm25', pm25)
	post_api_metric('pm10', pm10)

# Send a new status with value of PM2.5 and PM10
def sendTweet(pm25, pm10):
    if twitter is None:
        return
    twitter.update_status(status='For now, there are ' + str(pm25) + ' µg/m3 of PM2.5 and ' + str(pm10) + ' µg/m3 of PM10')

def publish_measurement(pm25, pm10):
	try:
		sendAdafruit(pm25, pm10)
	except Exception as exc:
		logger.exception('Failed to publish measurement to Adafruit IO: %s', exc)

	try:
		sendAPI(pm25, pm10)
	except (error.URLError, error.HTTPError, TimeoutError, RuntimeError) as exc:
		logger.warning('Failed to publish measurement to API: %s', exc)
	except Exception as exc:
		logger.exception('Unexpected API publish failure: %s', exc)

def main():
	global ser

	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s %(levelname)s %(message)s',
	)
	configure_clients()
	configure_display()
	try:
		initialize_serial()
		pm25, pm10 = takeMeasure()
		write_measurement_display(pm25, pm10)
		sendTweet(pm25, pm10)
	except (TimeoutError, serial.SerialException) as exc:
		ser = None
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
			write_measurement_display(pm25, pm10)
			publish_measurement(pm25, pm10)
			time.sleep(PROBE_WRITING_DELAY)
		except (TimeoutError, serial.SerialException) as exc:
			ser = None
			write_display('Air quality', 'Sensor error', 'Retrying...')
			logger.exception('SDS011 read failed: %s', exc)
			time.sleep(ERROR_RETRY_DELAY)
		except Exception as exc:
			write_display('Air quality', 'Publish error', 'See logs')
			logger.exception('Failed to publish measurement: %s', exc)
			time.sleep(ERROR_RETRY_DELAY)
	
if __name__ == '__main__':
    main()
