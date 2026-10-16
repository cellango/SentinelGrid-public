package main

import (
	"fmt"
	"os"

	"sentinelgrid-ai-shield/gateway/internal/httpapi"
	"sentinelgrid-ai-shield/gateway/internal/middleware"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	// Load environment variables
	_ = godotenv.Load()

	// Configure logging
	logLevel := os.Getenv("LOG_LEVEL")
	if logLevel == "" {
		logLevel = "info"
	}
	
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	level, err := zerolog.ParseLevel(logLevel)
	if err != nil {
		level = zerolog.InfoLevel
	}
	zerolog.SetGlobalLevel(level)
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	// Get configuration
	servicesURL := os.Getenv("SERVICES_URL")
	if servicesURL == "" {
		servicesURL = "http://localhost:8000"
	}

	telemetryMode := os.Getenv("TELEMETRY_MODE")
	if telemetryMode == "" {
		telemetryMode = "stdout"
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Info().
		Str("services_url", servicesURL).
		Str("telemetry_mode", telemetryMode).
		Str("port", port).
		Msg("Starting SentinelGridAIShield Gateway")

	// Create Gin router
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()

	// Apply middleware
	router.Use(middleware.Logger())
	router.Use(middleware.Recovery())
	router.Use(middleware.CORS())

	// Setup routes
	httpapi.SetupRoutes(router, servicesURL, telemetryMode)

	// Start server
	addr := fmt.Sprintf("0.0.0.0:%s", port)
	log.Info().Msgf("Gateway listening on %s", addr)
	
	if err := router.Run(addr); err != nil {
		log.Fatal().Err(err).Msg("Failed to start gateway")
	}
}

