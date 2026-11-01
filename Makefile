.PHONY: install run test clean db-up db-down db-logs

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

run:
	uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v tests/

clean:
	rm -rf _data __pycache__ .pytest_cache src/__pycache__ src/adapters/__pycache__ tests/__pycache__

db-up:
	docker compose up -d

db-down:
	docker compose down

db-logs:
	docker compose logs -f db
