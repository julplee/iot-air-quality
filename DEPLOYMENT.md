# Deployment

This repository has two deployable parts:

- `app/`: Python collector that runs on the Raspberry Pi attached to the SDS011 sensor
- `api/`: Go API that stores PM2.5 and PM10 readings

Recommended default architecture:

- keep the collector on the Raspberry Pi
- run the API either on the same Pi or on a small Debian VPS
- start both with `systemd`
- use SQLite first for the API
- put Caddy in front of the API only if you need HTTPS or public exposure

## Recommended operating model

### Option A: simplest

Run both the collector and the API on the Raspberry Pi.

Use this when:

- there is one sensor
- you mostly need local collection and a small API
- you want the least operational overhead

Set:

- `API_BASE_URL=http://127.0.0.1:3000`
- API `SERVER_ADDRESS=127.0.0.1:3000`
- API `DB_DIALECT=sqlite`

### Option B: better separation

Run the collector on the Raspberry Pi and the API on a Debian VPS.

Use this when:

- the API needs to be reachable even if the Pi is rebooting
- you want easier backups and remote access
- you may add more sensors later

Set:

- `API_BASE_URL=https://your-api-domain`
- API behind Caddy on the VPS
- API `DB_DIALECT=sqlite` at first, move to Postgres or MySQL later only if needed

## Collector deployment on Raspberry Pi

### 1. Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

If the display is connected over I2C, also enable I2C on the Pi and install whatever board-specific packages are needed for Blinka.

### 2. Create the app directory

```bash
sudo mkdir -p /opt/iot-air-quality/deploy
sudo mkdir -p /opt/iot-air-quality/app
sudo chown -R julien:julien /opt/iot-air-quality
```

Copy:

- the contents of `app/` into `/opt/iot-air-quality/app`
- the contents of `deploy/` into `/opt/iot-air-quality/deploy`

If you are on your Windows machine in the parent directory of this repo and you access the Pi over SSH, these commands copy the contents directly:

```bash
scp -r iot-air-quality/app/* julien@piblack:/opt/iot-air-quality/app/
scp -r iot-air-quality/deploy/* julien@piblack:/opt/iot-air-quality/deploy/
```

Do not edit files directly on the Pi with `nano` as the main workflow. Treat the Git repo as the source of truth and deploy from it.

### 3. Create the virtual environment

```bash
cd /opt/iot-air-quality/app
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install pyserial adafruit-io twython
pip install adafruit-circuitpython-ssd1306 pillow
```

If the display is disabled, the second `pip install` line can be skipped.

### 4. Install environment file

```bash
sudo mkdir -p /etc/iot-air-quality
sudo cp /opt/iot-air-quality/deploy/env/app.env.example /etc/iot-air-quality/app.env
sudo chmod 600 /etc/iot-air-quality/app.env
```

If you do not copy `deploy/` onto the Pi, copy [`deploy/env/app.env.example`](/d:/dev/iot-air-quality/deploy/env/app.env.example) from this repo by some other means and create `/etc/iot-air-quality/app.env`.

### 5. Install the systemd unit

```bash
sudo cp /opt/iot-air-quality/deploy/systemd/iot-air-quality-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now iot-air-quality-app
```

### 6. Operate it

```bash
sudo systemctl status iot-air-quality-app
sudo journalctl -u iot-air-quality-app -f
sudo systemctl restart iot-air-quality-app
```

## API deployment on Pi or VPS

### 1. Install packages

```bash
sudo apt update
sudo apt install -y golang-go
```

### 2. Create runtime user and directories

```bash
sudo mkdir -p /opt/iot-air-quality/deploy
sudo useradd --system --home /opt/iot-air-quality/api --shell /usr/sbin/nologin iotair
sudo mkdir -p /opt/iot-air-quality/api
sudo mkdir -p /var/lib/iot-air-quality
sudo chown -R iotair:iotair /opt/iot-air-quality/api /var/lib/iot-air-quality
sudo chown -R root:root /opt/iot-air-quality/deploy
```

### 3. Build the binary

```bash
cd /opt/iot-air-quality/api
go build -o iot-air-quality-api .
```

If you build elsewhere, copy the resulting binary to `/opt/iot-air-quality/api/iot-air-quality-api`.

### 4. Install environment file

```bash
sudo mkdir -p /etc/iot-air-quality
sudo cp /opt/iot-air-quality/deploy/env/api.env.example /etc/iot-air-quality/api.env
sudo chmod 600 /etc/iot-air-quality/api.env
```

For this project, SQLite is the right starting point. The API already supports it through `DB_DIALECT=sqlite` and `DB_PATH`.

### 5. Install the systemd unit

```bash
sudo cp /opt/iot-air-quality/deploy/systemd/iot-air-quality-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now iot-air-quality-api
```

### 6. Validate the API

```bash
curl http://127.0.0.1:3000/healthz
curl http://127.0.0.1:3000/readyz
curl http://127.0.0.1:3000/pm25
```

### 7. Operate it

```bash
sudo systemctl status iot-air-quality-api
sudo journalctl -u iot-air-quality-api -f
sudo systemctl restart iot-air-quality-api
```

## Public HTTPS for the API

If you want public HTTPS, put Caddy in front of the API and keep the Go service bound to `127.0.0.1:3000`.

Minimal Caddyfile:

```caddyfile
air.example.com {
    reverse_proxy 127.0.0.1:3000
}
```

Then set the collector `API_BASE_URL` to `https://air.example.com`.

If you do not need public exposure, Tailscale is a better fit than opening the API to the internet.

## Deployment workflow

Use one of these, in this order of preference:

1. `git pull` on the host if the repo exists there
2. `rsync` from your workstation to the host
3. a small script that copies the changed files, rebuilds the API, and restarts the relevant service

Avoid hand-editing production files with `nano` except for emergency fixes.

## Backup

If the API uses SQLite, back up:

- `/var/lib/iot-air-quality/iot-air-quality.db`
- `/etc/iot-air-quality/api.env`
- `/etc/iot-air-quality/app.env`

If you want longer retention or analytics later, the first upgrade should be better backup/export handling, not a more complex orchestrator.

## Known hardening gap

The collector currently opens the serial port during module import, before `main()` starts. That behavior lives in [`app/air-quality.py`](/d:/dev/iot-air-quality/app/air-quality.py#L52). Moving serial initialization into startup logic would make service restarts and boot-time failures cleaner under `systemd`.
