.PHONY: all build up down test smoke logs clean

all: build

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down -v

test:
	pytest services/catalog-api/tests -v
	pytest services/order-worker/tests -v

smoke:
	bash scripts/smoke-test.sh

logs:
	docker compose logs -f

clean:
	docker compose down -v --remove-orphans
