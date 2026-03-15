# iot-air-quality
Code that handles IOT for Air Quality monitoring with Raspberry Pi

## Running the Air Quality Script

### Startup mechanism

The script is automatically started at system boot using root's cron.

The cron entry is:

```bash
sudo crontab -l
```

Expected entry:

```bash
@reboot sleep 30 && python3 /usr/lib/iot-air-quality/air-quality.py
```

The sleep 30 allows the system and network to finish initializing before the script starts.

The script now reads configuration from a `.env` file stored next to `air-quality.py`. This is important when starting from cron because `@reboot` does not inherit your interactive shell environment.

## Prerequisites
`pip3 install pyserial adafruit-io twython`

For the SSD1306 display on Raspberry Pi, also install:
`pip3 install adafruit-circuitpython-ssd1306 pillow`

This project expects an SDS011 particulate matter sensor connected over a serial port. The production script reads SDS011 data frames and publishes PM2.5 and PM10 values to Adafruit IO. It can also post readings to the Go API in this repository and send one startup tweet with the first successful reading when Twitter posting is enabled.

## Configuration
Create a `.env` file next to `air-quality.py`, or export these variables before launching the script:

`ADAFRUIT_IO_USERNAME`
`ADAFRUIT_IO_KEY`
`TWITTER_APP_KEY`
`TWITTER_APP_SECRET`
`TWITTER_OAUTH_TOKEN`
`TWITTER_OAUTH_TOKEN_SECRET`

Optional environment variables:

`SDS011_SERIAL_PORT` defaults to `/dev/ttyUSB0` in `air-quality.py` and `COM4` in `test-sensor.py`
`ADAFRUIT_IO_PM25_FEED` defaults to `kingswoodtwofive`
`ADAFRUIT_IO_PM10_FEED` defaults to `kingswoodten`
`API_BASE_URL` optional; when set, the script also posts to `/pm25` and `/pm10` on that API base URL
`API_TIMEOUT_SECONDS` defaults to `5`
`ENABLE_TWITTER` defaults to `false`; set it to `true` only if your X/Twitter API access level supports posting statuses
`ENABLE_DISPLAY` defaults to `true`
`DISPLAY_WIDTH` defaults to `128`
`DISPLAY_HEIGHT` defaults to `64`
`DISPLAY_I2C_ADDRESS` defaults to `0x3C`

PowerShell example:
`$env:SDS011_SERIAL_PORT='COM4'`
`$env:ADAFRUIT_IO_USERNAME='your-username'`
`$env:ADAFRUIT_IO_KEY='your-aio-key'`
$env:API_BASE_URL='http://127.0.0.1:3000'
`$env:ENABLE_TWITTER='true'`
`$env:TWITTER_APP_KEY='your-app-key'`
`$env:TWITTER_APP_SECRET='your-app-secret'`
`$env:TWITTER_OAUTH_TOKEN='your-oauth-token'`
`$env:TWITTER_OAUTH_TOKEN_SECRET='your-oauth-token-secret'`

`.env` example:
`ADAFRUIT_IO_USERNAME=your-username`
`ADAFRUIT_IO_KEY=your-aio-key`
`API_BASE_URL=http://127.0.0.1:3000`
`SDS011_SERIAL_PORT=/dev/ttyUSB0`
`ENABLE_TWITTER=false`
`ENABLE_DISPLAY=true`
`DISPLAY_WIDTH=128`
`DISPLAY_HEIGHT=64`
`DISPLAY_I2C_ADDRESS=0x3C`

## Runtime behavior
`air-quality.py` validates SDS011 frame headers, footers, and checksums before decoding measurements.

If the sensor stops responding or a publish call fails, the script logs the error and retries instead of exiting. Serial reads time out after 5 seconds.

Adafruit IO and API publishing are attempted independently. If the Go API is unavailable, the collector still keeps updating Adafruit IO and the display.

Twitter posting is disabled by default so the collector can run with Adafruit IO only. When enabled, a Twitter/X API posting failure is logged but does not stop measurement uploads.

When the SSD1306 dependencies are installed and the display is connected over I2C, the script shows startup state, the latest PM2.5 and PM10 values, and simple retry/error messages on the screen. If the display cannot be initialized, the collector keeps running and logs a warning.

`test-sensor.py` is a local console reader for checking raw SDS011 measurements on a serial port. It does not publish to Adafruit IO or Twitter.

## Launch the project
`python3 air-quality.py`
