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

This project expects an SDS011 particulate matter sensor connected over a serial port. The production script reads SDS011 data frames and publishes PM2.5 and PM10 values to Adafruit IO. It can also post one startup tweet with the first successful reading when Twitter posting is enabled.

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
`ENABLE_TWITTER` defaults to `false`; set it to `true` only if your X/Twitter API access level supports posting statuses

PowerShell example:
`$env:SDS011_SERIAL_PORT='COM4'`
`$env:ADAFRUIT_IO_USERNAME='your-username'`
`$env:ADAFRUIT_IO_KEY='your-aio-key'`
`$env:ENABLE_TWITTER='true'`
`$env:TWITTER_APP_KEY='your-app-key'`
`$env:TWITTER_APP_SECRET='your-app-secret'`
`$env:TWITTER_OAUTH_TOKEN='your-oauth-token'`
`$env:TWITTER_OAUTH_TOKEN_SECRET='your-oauth-token-secret'`

`.env` example:
`ADAFRUIT_IO_USERNAME=your-username`
`ADAFRUIT_IO_KEY=your-aio-key`
`SDS011_SERIAL_PORT=/dev/ttyUSB0`
`ENABLE_TWITTER=false`

## Runtime behavior
`air-quality.py` validates SDS011 frame headers, footers, and checksums before decoding measurements.

If the sensor stops responding or a publish call fails, the script logs the error and retries instead of exiting. Serial reads time out after 5 seconds.

Twitter posting is disabled by default so the collector can run with Adafruit IO only. When enabled, a Twitter/X API posting failure is logged but does not stop measurement uploads.

`test-sensor.py` is a local console reader for checking raw SDS011 measurements on a serial port. It does not publish to Adafruit IO or Twitter.

## Launch the project
`python3 air-quality.py`
