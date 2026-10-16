.PHONY: test test-gateway test-services up down

test: test-gateway test-services

test-gateway:
	$(MAKE) -C gateway test

test-services:
	cd services && pytest -v

up:
	docker compose up --build

down:
	docker compose down
