.PHONY: up down test seed collect
up:
	docker compose up --build

down:
	docker compose down

test:
	pytest -q

seed:
	python scripts/seed_demo.py

collect:
	python scripts/collect_once.py
