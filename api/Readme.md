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

Required:

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

### Build & run

```bash
go build
./iot-air-quality-api
```
