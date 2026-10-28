# Haathi — Mac (Apple Silicon) developer workflow (haathi.md §4.1)
SHELL := /bin/zsh
UV := $(shell command -v uv 2>/dev/null || echo $$HOME/.local/bin/uv)
BACKEND := backend
FRONTEND := frontend



.PHONY: eval-quick stop setup setup-ml services services-tracing ingest ingest-download dev backend frontend eval test loadtest freshness icons phone

setup:            ## install Python + Node dependencies
	cd $(BACKEND) && $(UV) sync --python 3.12
	cd $(FRONTEND) && npm install

setup-ml:         ## add BGE-M3, bge-reranker-v2-m3 and Docling (runs on the Mac GPU via MPS; ~3 GB download)
	cd $(BACKEND) && $(UV) sync --python 3.12 --extra ml

services:         ## start Qdrant (optional: the app also runs Qdrant in-process)
	docker compose up -d qdrant

services-tracing: ## start Qdrant + Langfuse
	docker compose --profile tracing up -d

ingest:           ## parse, chunk, contextualize and index the corpus
	cd $(BACKEND) && $(UV) run python -m ingestion.run

ingest-download:  ## download official documents from data/manifest.csv first, then ingest + extract rules
	cd $(BACKEND) && $(UV) run python -m ingestion.run --download --extract

dev:              ## run backend and frontend together
	$(MAKE) -j2 backend frontend

stop:             ## stop Haathi's servers and wait until ports 8000 and 3000 are free
	-@pkill -f "uvicorn app.main:app" 2>/dev/null; pkill -f "next dev" 2>/dev/null; pkill -f "next start" 2>/dev/null; \
	for i in 1 2 3 4 5 6 7 8 9 10; do lsof -ti tcp:8000 -sTCP:LISTEN >/dev/null || lsof -ti tcp:3000 -sTCP:LISTEN >/dev/null || break; \
	  lsof -ti tcp:8000 -sTCP:LISTEN | xargs kill 2>/dev/null; lsof -ti tcp:3000 -sTCP:LISTEN | xargs kill 2>/dev/null; sleep 1; done; \
	echo "ports 8000 and 3000 are free"

backend:
	cd $(BACKEND) && $(UV) run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app --reload-dir ingestion --reload-dir admin

frontend:
	cd $(FRONTEND) && npm run dev -- -H 0.0.0.0 -p 3000

test:             ## unit + API tests with coverage for the eligibility engine
	cd $(BACKEND) && $(UV) run pytest -q --cov=app.eligibility --cov-report=term-missing

eval-quick:       ## main benchmark + rule engine vs Gemini-only (fits the free Gemini quota better)
	cd $(BACKEND) && $(UV) run python ../eval/run_eval.py
	cd $(BACKEND) && $(UV) run python ../eval/eligibility_compare.py

eval:             ## benchmark, ablations, risk–coverage, questioning, eligibility comparison
	cd $(BACKEND) && $(UV) run python ../eval/run_eval.py
	cd $(BACKEND) && $(UV) run python ../eval/ablations.py
	cd $(BACKEND) && $(UV) run python ../eval/risk_coverage.py
	cd $(BACKEND) && $(UV) run python ../eval/questioning.py
	cd $(BACKEND) && $(UV) run python ../eval/eligibility_compare.py

loadtest:         ## Locust: 20 then 50 concurrent users (backend must be running)
	cd $(BACKEND) && $(UV) run --extra loadtest locust -f locustfile.py --headless -u 20 -r 5 -t 60s --host http://localhost:8000 --csv ../eval/reports/load_20
	cd $(BACKEND) && $(UV) run --extra loadtest locust -f locustfile.py --headless -u 50 -r 10 -t 60s --host http://localhost:8000 --csv ../eval/reports/load_50

freshness:        ## weekly: re-download, diff, re-extract changed schemes
	cd $(BACKEND) && $(UV) run python -m ingestion.freshness

icons:            ## export all PNG/ICO sizes from public/icons/icon.svg
	cd $(FRONTEND) && npm run icons

phone:            ## print the URL to open on your phone (same Wi-Fi)
	@echo "Open http://$$(ipconfig getifaddr en0):3000 on your phone"
