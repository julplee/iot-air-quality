package model

import (
	"gorm.io/gorm"
)

type PM25 struct {
	gorm.Model
	Value float64 `json:"value"`
}

type PM10 struct {
	gorm.Model
	Value float64 `json:"value"`
}

func DBMigrate(db *gorm.DB) (*gorm.DB, error) {
	if err := db.AutoMigrate(&PM25{}, &PM10{}); err != nil {
		return nil, err
	}

	return db, nil
}
