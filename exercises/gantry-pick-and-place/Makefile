.PHONY: up down logs test test-backend test-frontend dev

# Build and start the whole stack (backend + frontend).
up:
	docker compose up --build

# Stop and remove the stack.
down:
	docker compose down

# Tail logs from all services.
logs:
	docker compose logs -f

# Run backend tests in a one-off container.
test-backend:
	docker compose run --rm backend pytest -q

# Run frontend tests in a one-off container.
test-frontend:
	docker compose run --rm frontend npm test --silent

# Run both test suites.
test: test-backend test-frontend

# Native (non-Docker) path. The backend needs Python 3.10 (use pyenv), the
# frontend needs npm. Docker (make up) is the canonical path; this is a reminder.
dev:
	@echo "Native dev (Docker via 'make up' is the canonical path):"
	@echo ""
	@echo "  Backend (requires Python 3.10, e.g. via pyenv):"
	@echo "    cd backend && python -m venv venv && source venv/bin/activate"
	@echo "    pip install -r requirements.txt"
	@echo "    uvicorn main:app --reload --port 8000"
	@echo ""
	@echo "  Frontend (in a second terminal):"
	@echo "    cd frontend && npm install && npm run dev"
