package app

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/gorilla/mux"
	"github.com/julplee/iot-air-quality-api/app/handler"
	"github.com/julplee/iot-air-quality-api/app/model"
	"github.com/julplee/iot-air-quality-api/config"
	"gorm.io/driver/mysql"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// App has a Router and a Database
type App struct {
	Router         *mux.Router
	DB             *gorm.DB
	server         *http.Server
	shutdownTimout time.Duration
}

// Initialize initializes the app with predefined configuration
func (a *App) Initialize(config *config.Config) error {
	db, err := openDB(config.DB)
	if err != nil {
		return fmt.Errorf("could not connect to database: %w", err)
	}

	a.DB, err = model.DBMigrate(db)
	if err != nil {
		return fmt.Errorf("could not migrate database: %w", err)
	}

	a.Router = mux.NewRouter()
	a.setRouters()
	a.server = &http.Server{
		Addr:    config.Server.Address,
		Handler: a.Router,
	}
	a.shutdownTimout = time.Duration(config.Server.ShutdownTimeoutSeconds) * time.Second

	return nil
}

func openDB(dbConfig *config.DBConfig) (*gorm.DB, error) {
	switch strings.ToLower(dbConfig.Dialect) {
	case "mysql":
		dbURI := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=%s&parseTime=True",
			dbConfig.Username,
			dbConfig.Password,
			dbConfig.Host,
			dbConfig.Port,
			dbConfig.Name,
			dbConfig.Charset)

		return gorm.Open(mysql.Open(dbURI), &gorm.Config{})
	case "sqlite":
		return gorm.Open(sqlite.Open(dbConfig.Path), &gorm.Config{})
	default:
		return nil, fmt.Errorf("unsupported DB_DIALECT %q; supported values are mysql and sqlite", dbConfig.Dialect)
	}
}

func (a *App) setRouters() {
	a.Router.HandleFunc("/healthz", a.healthHandler).Methods("GET")
	a.Router.HandleFunc("/readyz", a.readyHandler).Methods("GET")
	a.Get("/pm25", a.handleRequest(handler.GetAllPM25))
	a.Post("/pm25", a.handleRequest(handler.CreatePM25))
	a.Get("/pm10", a.handleRequest(handler.GetAllPM10))
	a.Post("/pm10", a.handleRequest(handler.CreatePM10))
}

// Get wraps the router for GET HTTP method
func (a *App) Get(path string, f func(w http.ResponseWriter, r *http.Request)) {
	a.Router.HandleFunc(path, f).Methods("GET")
}

// Post wraps the router for POST HTTP method
func (a *App) Post(path string, f func(w http.ResponseWriter, r *http.Request)) {
	a.Router.HandleFunc(path, f).Methods("POST")
}

// Run the app on its router
func (a *App) Run() error {
	if a.server == nil {
		return fmt.Errorf("server is not initialized")
	}

	shutdownContext, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	serverErrors := make(chan error, 1)
	go func() {
		log.Printf("level=info msg=\"starting server\" address=%q", a.server.Addr)
		err := a.server.ListenAndServe()
		if err != nil && !errors.Is(err, http.ErrServerClosed) {
			serverErrors <- err
			return
		}
		serverErrors <- nil
	}()

	select {
	case err := <-serverErrors:
		if err != nil {
			return fmt.Errorf("http server failed: %w", err)
		}
		return nil
	case <-shutdownContext.Done():
		log.Printf("level=info msg=\"shutdown signal received\"")
	}

	ctx, cancel := context.WithTimeout(context.Background(), a.shutdownTimout)
	defer cancel()

	if err := a.server.Shutdown(ctx); err != nil {
		return fmt.Errorf("graceful shutdown failed: %w", err)
	}

	log.Printf("level=info msg=\"server stopped gracefully\"")
	return nil
}

// RequestHandlerFunction defines a handler function for an HTTP request
type RequestHandlerFunction func(db *gorm.DB, w http.ResponseWriter, r *http.Request)

func (a *App) handleRequest(handler RequestHandlerFunction) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		handler(a.DB, w, r)
	}
}

func (a *App) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ok"))
}

func (a *App) readyHandler(w http.ResponseWriter, r *http.Request) {
	sqlDB, err := a.DB.DB()
	if err != nil {
		http.Error(w, "database unavailable", http.StatusServiceUnavailable)
		return
	}

	if err := sqlDB.PingContext(r.Context()); err != nil {
		http.Error(w, "database unavailable", http.StatusServiceUnavailable)
		return
	}

	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ready"))
}
