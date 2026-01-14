demo:
	bash scripts/demo.sh

reset:
	docker compose down -v

up:
	docker compose up -d --build

seed:
	docker compose exec -T backend python -m app.seed

test:
	docker compose exec -T backend pytest -q

smoke:
	bash scripts/smoke_demo.sh

logs:
	docker compose logs -f --tail=100
