# Makefile for SentinelGridAIShield Gateway

.PHONY: build test clean run docker-build docker-run

# Build the gateway
build:
	go build -o bin/gateway ./cmd/gateway

# Run tests
test:
	go test -v ./...

# Run tests with coverage
test-coverage:
	go test -v -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html

# Clean build artifacts
clean:
	rm -rf bin/
	rm -f coverage.out coverage.html

# Run the gateway locally
run:
	go run ./cmd/gateway

# Build Docker image
docker-build:
	docker build -t sentinelgrid/sentinelgrid-ai-shield-gateway:latest .

# Run Docker container
docker-run:
	@test -n "$$SERVICES_URL" || (echo "Set SERVICES_URL before running docker-run" && exit 1)
	docker run -p 8080:8080 \
		-e SERVICES_URL=$$SERVICES_URL \
		-e INTERNAL_SERVICE_TOKEN=internal-service-token-change-in-production \
		-e TELEMETRY_MODE=stdout \
		sentinelgrid/sentinelgrid-ai-shield-gateway:latest

# Format code
fmt:
	go fmt ./...

# Lint code
lint:
	golangci-lint run

# Download dependencies
deps:
	go mod download
	go mod tidy
