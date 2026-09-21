.PHONY: up down test lint seed demo help

help:
	@echo "SkySafe AI Management Commands:"
	@echo "  make up     - Start all docker containers"
	@echo "  make down   - Stop and remove all docker containers"
	@echo "  make test   - Run backend tests"
	@echo "  make lint   - Run python code quality checks"
	@echo "  make seed   - Execute data seeding script"
	@echo "  make demo   - Run interactive/automated demo scenario"

up:
	docker compose up -d --build

down:
	docker compose down -v

test:
	python -m pytest backend/tests

lint:
	python -m ruff check backend

seed:
	python scripts/seed.py

demo:
	python scripts/demo.py
