package config

import (
	"fmt"
	"os"
	"strconv"
)

// Config contains a database configuration
type Config struct {
	DB     *DBConfig
	Server *ServerConfig
}

// DBConfig contains the configuration of the database
type DBConfig struct {
	Dialect  string
	Host     string
	Port     int
	Username string
	Password string
	Name     string
	Charset  string
}

// ServerConfig contains the configuration of the HTTP server
type ServerConfig struct {
	Address                string
	ShutdownTimeoutSeconds int
}

// GetConfig gets the configuration of the database
func GetConfig() (*Config, error) {
	password := os.Getenv("DB_PASSWORD")
	if password == "" {
		return nil, fmt.Errorf("DB_PASSWORD is required")
	}

	port, err := getEnvAsInt("DB_PORT", 3306)
	if err != nil {
		return nil, err
	}

	return &Config{
		DB: &DBConfig{
			Dialect:  getEnv("DB_DIALECT", "mysql"),
			Host:     getEnv("DB_HOST", "127.0.0.1"),
			Port:     port,
			Username: getEnv("DB_USERNAME", "guest"),
			Password: password,
			Name:     getEnv("DB_NAME", "iot-air-quality"),
			Charset:  getEnv("DB_CHARSET", "utf8"),
		},
		Server: &ServerConfig{
			Address:                getEnv("SERVER_ADDRESS", ":3000"),
			ShutdownTimeoutSeconds: getEnvAsIntOrDefault("SHUTDOWN_TIMEOUT_SECONDS", 10),
		},
	}, nil
}

func getEnv(key string, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}

	return value
}

func getEnvAsInt(key string, fallback int) (int, error) {
	value := os.Getenv(key)
	if value == "" {
		return fallback, nil
	}

	parsed, err := strconv.Atoi(value)
	if err != nil {
		return 0, fmt.Errorf("%s must be a valid integer", key)
	}

	return parsed, nil
}

func getEnvAsIntOrDefault(key string, fallback int) int {
	value, err := getEnvAsInt(key, fallback)
	if err != nil {
		return fallback
	}

	return value
}
