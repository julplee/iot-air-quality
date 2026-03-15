package handler

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"

	"github.com/julplee/iot-air-quality-api/app/model"
	"gorm.io/gorm"
)

type createPM25Request struct {
	Value float64 `json:"value"`
}

const maxPM25BodyBytes int64 = 1024

func GetAllPM25(db *gorm.DB, w http.ResponseWriter, r *http.Request) {
	pm25s := []model.PM25{}

	limit, offset, err := parsePagination(r)
	if err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := db.Order("created_at DESC").Limit(limit).Offset(offset).Find(&pm25s).Error; err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}

	respondJSON(w, http.StatusOK, pm25s)
}

func CreatePM25(db *gorm.DB, w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()

	r.Body = http.MaxBytesReader(w, r.Body, maxPM25BodyBytes)

	request := createPM25Request{}
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

	pm25 := model.PM25{
		Value: request.Value,
	}

	if err := db.Create(&pm25).Error; err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}

	respondJSON(w, http.StatusCreated, pm25)
}
