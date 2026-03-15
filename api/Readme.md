# Go API for IOT Air Quality

see: <https://github.com/julplee/iot-air-quality>

A RESTful API to store IOT metrics with Go using gorilla/mux (API library) and Gorm (ORM for Go)

Available endpoints:

- `GET /healthz`
- `GET /readyz`
- `GET /pm25`
- `POST /pm25`
- `GET /pm10`
- `POST /pm10`

List endpoints support:

- `limit` optional, default `100`, max `1000`
- `offset` optional, default `0`
- results ordered by newest first

## Installation & run

### Download this project

```bash
git clone https://github.com/julplee/iot-air-quality-api.git
cd iot-air-quality-api
go mod tidy
```

Before running API server, configure the database with environment variables.

Required for MySQL:

```bash
export DB_PASSWORD=your-database-password
```

Optional:

```bash
export DB_DIALECT=mysql
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USERNAME=guest
export DB_NAME=iot-air-quality
export DB_CHARSET=utf8
export SERVER_ADDRESS=:3000
export SHUTDOWN_TIMEOUT_SECONDS=10
```

Supported database dialects:

- `mysql` uses `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME`, `DB_CHARSET`
- `sqlite` uses `DB_PATH` and ignores the MySQL-specific settings

SQLite example:

```bash
export DB_DIALECT=sqlite
export DB_PATH=./iot-air-quality.db
```

## Deployment recommendation

For this repository, the lowest-friction deployment is:

- run the sensor collector on the Raspberry Pi with `systemd`
- run this API with `systemd`
- use `sqlite` first
- optionally put Caddy in front if you need HTTPS

See [`DEPLOYMENT.md`](/d:/dev/iot-air-quality/DEPLOYMENT.md) for the concrete setup, example env files, and `systemd` unit files.

### Build & run

```bash
go build
./iot-air-quality-api
```
