# iot-air-quality
Code that handles IOT for Air Quality monitoring with Raspberry Pi

## Prerequisites
`pip3 install pyserial adafruit-io twython`

## Configuration
Set these environment variables before launching the script:

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

PowerShell example:
`$env:ADAFRUIT_IO_USERNAME='your-username'`

## Launch the project
`python3 air-quality.py`
