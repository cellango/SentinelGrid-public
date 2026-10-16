SHELL := /bin/sh

.PHONY: all build test lint run-server run-client

all: build

build:
	go build ./...

test:
	go test ./...

lint:
	go vet ./...

run-server:
	go run ./server

run-client:
	go run ./client

.PHONY: test-e2e
test-e2e:
	./test/e2e.sh
