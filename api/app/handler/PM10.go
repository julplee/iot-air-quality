package handler

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"

	"github.com/julplee/iot-air-quality-api/app/model"
	"gorm.io/gorm"
)

type createPM10Request struct {
	Value float64 `json:"value"`
}

const maxPM10BodyBytes int64 = 1024

func GetAllPM10(db *gorm.DB, w http.ResponseWriter, r *http.Request) {
	pm10s := []model.PM10{}

	if err := db.Find(&pm10s).Error; err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}

	respondJSON(w, http.StatusOK, pm10s)
}

func CreatePM10(db *gorm.DB, w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()

	r.Body = http.MaxBytesReader(w, r.Body, maxPM10BodyBytes)

	request := createPM10Request{}
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()

	if err := decoder.Decode(&request); err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := validateMetricValue(request.Value); err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	pm10 := model.PM10{
		Value: request.Value,
	}

	if err := db.Create(&pm10).Error; err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}

	respondJSON(w, http.StatusCreated, pm10)
}
