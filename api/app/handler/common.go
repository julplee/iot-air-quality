package handler

import (
	"encoding/json"
	"errors"
	"math"
	"net/http"
	"strconv"
)

const (
	defaultListLimit = 100
	maxListLimit     = 1000
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

func parsePagination(r *http.Request) (int, int, error) {
	query := r.URL.Query()

	limit := defaultListLimit
	if rawLimit := query.Get("limit"); rawLimit != "" {
		parsedLimit, err := strconv.Atoi(rawLimit)
		if err != nil {
			return 0, 0, errors.New("limit must be a valid integer")
		}
		if parsedLimit <= 0 {
			return 0, 0, errors.New("limit must be greater than 0")
		}
		if parsedLimit > maxListLimit {
			return 0, 0, errors.New("limit must be less than or equal to 1000")
		}
		limit = parsedLimit
	}

	offset := 0
	if rawOffset := query.Get("offset"); rawOffset != "" {
		parsedOffset, err := strconv.Atoi(rawOffset)
		if err != nil {
			return 0, 0, errors.New("offset must be a valid integer")
		}
		if parsedOffset < 0 {
			return 0, 0, errors.New("offset must be greater than or equal to 0")
		}
		offset = parsedOffset
	}

	return limit, offset, nil
}
