package handler

import (
	"encoding/json"
	"errors"
	"math"
	"net/http"
)

func respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	response, err := json.Marshal(payload)

	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	w.Write([]byte(response))
}

func respondError(w http.ResponseWriter, code int, message string) {
	respondJSON(w, code, map[string]string{"error": message})
}

func validateMetricValue(value float64) error {
	switch {
	case math.IsNaN(value), math.IsInf(value, 0):
		return errors.New("value must be a finite number")
	case value < 0:
		return errors.New("value must be greater than or equal to 0")
	default:
		return nil
	}
}
