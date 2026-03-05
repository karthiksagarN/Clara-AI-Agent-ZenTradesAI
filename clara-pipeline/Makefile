.PHONY: setup install ollama-pull run-demo run-onboarding run-all n8n-up n8n-down clean test help

# Default target
help:
	@echo "Clara Pipeline — Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          — Full setup (install deps + pull model)"
	@echo "  make install        — Install Python dependencies"
	@echo "  make ollama-pull    — Pull Llama 3.1 8B model"
	@echo ""
	@echo "Run Pipelines:"
	@echo "  make run-demo       — Run Pipeline A on all demo files"
	@echo "  make run-onboarding — Run Pipeline B on all onboarding files"
	@echo "  make run-all        — Run both pipelines on all files"
	@echo ""
	@echo "Orchestration:"
	@echo "  make n8n-up         — Start n8n via Docker"
	@echo "  make n8n-down       — Stop n8n"
	@echo ""
	@echo "Other:"
	@echo "  make test           — Run tests"
	@echo "  make clean          — Clean generated outputs"
	@echo "  make diff-viewer    — Generate HTML diff viewer"

# ---- Setup ----

setup: install ollama-pull
	@echo "✅ Setup complete!"
	@echo "Next: Place transcripts in recordings/demo/ and recordings/onboarding/"
	@echo "Then: make run-all"

install:
	pip install -r requirements.txt
	@echo "✅ Python dependencies installed"

ollama-pull:
	@echo "Pulling Llama 3.1 8B model (this may take a few minutes)..."
	ollama pull llama3.1:8b
	@echo "✅ Model ready"

# ---- Pipelines ----

run-demo:
	cd scripts && python3 run_all.py --transcripts-only --onboarding-dir /dev/null 2>&1 || \
	cd scripts && python3 run_all.py --transcripts-only

run-onboarding:
	cd scripts && python3 run_all.py --transcripts-only --demo-dir /dev/null 2>&1 || \
	cd scripts && python3 run_all.py --transcripts-only

run-all:
	cd scripts && python3 run_all.py --transcripts-only

run-single-demo:
	@read -p "Enter transcript path: " path; \
	cd scripts && python3 run_pipeline_a.py "$$path" --skip-transcription

run-single-onboarding:
	@read -p "Enter transcript path: " path; \
	read -p "Enter company name: " company; \
	cd scripts && python3 run_pipeline_b.py "$$path" --company "$$company" --skip-transcription

# ---- Orchestration ----

n8n-up:
	docker-compose up -d
	@echo "✅ n8n running at http://localhost:5678"
	@echo "   User: admin | Password: changeme"

n8n-down:
	docker-compose down

# ---- Utilities ----

diff-viewer:
	cd scripts && python3 generate_diff_viewer.py

test:
	cd scripts && python3 -m pytest ../tests/ -v

clean:
	rm -rf outputs/accounts/*/
	rm -rf outputs/summary_report.json
	rm -rf changelog/*.md
	@echo "✅ Outputs cleaned"

# ---- Environment ----

env:
	@cp -n .env.example .env 2>/dev/null || true
	@echo "Edit .env file with your settings"
