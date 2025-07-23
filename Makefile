CC = uv

.PHONY
build:
	docker compose -f docker-compose.yml build --no-cache

.PHONY
up:
	docker compose -f docker-compose.yml up -d

.PHONY
down:
	docker compose -f docker-compose.yml down

.PHONY
logs:
	docker compose -f docker-compose.yml logs

.PHONY
run:
	$(CC) run main.py

