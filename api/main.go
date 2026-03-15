package main

import (
	"log"

	"github.com/julplee/iot-air-quality-api/app"
	"github.com/julplee/iot-air-quality-api/config"
)

func main() {
	config, err := config.GetConfig()
	if err != nil {
		log.Fatal(err)
	}

	app := &app.App{}
	if err := app.Initialize(config); err != nil {
		log.Fatal(err)
	}

	if err := app.Run(); err != nil {
		log.Fatal(err)
	}
}
