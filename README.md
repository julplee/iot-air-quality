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

PowerShell example:
`$env:ADAFRUIT_IO_USERNAME='your-username'`

## Launch the project
`python3 air-quality.py`
