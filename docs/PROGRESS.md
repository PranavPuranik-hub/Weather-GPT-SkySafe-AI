# SkySafe AI - Project Progress Log

## Status Overview
- [x] Initial Monorepo Setup (Prompt 1)
  - Backend FastAPI layout with 13 packages
  - Frontend Next.js PWA baseline
  - Docker Compose setup & Makefile targets
  - Baseline health check & unit test suite

## Detailed Log

### 2026-09-21 - Prompt 1: Monorepo Setup
- Initialized directory structure: `backend`, `frontend`, `data`, `docs`, `scripts`.
- Configured FastAPI application `skysafe` with pydantic-settings and `/health` endpoint.
- Built Next.js 14 PWA placeholder with mobile-first landing page and route links for Citizen view and Command dashboard.
- Configured PostgreSQL / PostGIS container service, Makefile targets (`up`, `down`, `test`, `lint`, `seed`, `demo`), and environment variables template.
### 2026-09-21 - Prompt 1 Fix: PostgreSQL Driver Dependency
- Added `psycopg2-binary>=2.9.9` dependency to `backend/requirements.txt` and `backend/pyproject.toml`.
- Added unit test `test_postgres_driver_import` to verify `postgresql://` URI engine initialization.
### 2026-09-21 - Prompt 1 Fix: /health Routing Resolution
- Resolved FastAPI empty path/prefix collision in `skysafe/api/health.py` by configuring explicit `/health` and `/health/` decorators on `health_router`.
- Verified GET `/health` and GET `/health/` return HTTP 200 with required JSON payload keys (`status`, `database`, `last_sachet_fetch`, `last_open_meteo_fetch`, `llm_provider`, `mode`).
### 2026-09-21 - Prompt 1 Fix: Docker Port Binding
- Updated `docker-compose.yml` backend service port mapping from `"8000:8000"` to `"0.0.0.0:8000:8000"`.
- Explicitly configured host binding so container port 8000 maps to `0.0.0.0:8000->8000/tcp`.
- All 16 backend unit tests pass.

### 2026-09-21 - Ingestion Layer (`skysafe/ingest`)
- Built resilient XML CAP 1.2 parser in `cap_parser.py` extracting identifier, status, note, info, area polygon, and GeoJSON geometry.
- Built NDMA SACHET RSS client (`sachet_client.py`) and IMD adapter (`imd_client.py`) with retry backoff and offline fixtures fallback.
- Implemented `OpenMeteoClient` (`open_meteo.py`) with typed models for forecast, marine, flood, and historical archive APIs with 15-minute in-memory caching and cached fallback.
- Added 9 realistic drill fixtures in `/data/fixtures/cap/` labeled with `<note>DRILL - SIMULATED</note>` and `<status>Exercise</status>` across Kerala, Odisha, Rajasthan, Bihar, Tamil Nadu coast, Uttarakhand, and Andhra Pradesh, plus expired alerts.
- Added matching offline fixtures for Open-Meteo in `/data/fixtures/open_meteo/`.
- Implemented `IngestService` (`service.py`) providing deduplication, history updates, expiration marking, and alert-to-ingest lag calculation (`now - sent`).
- Configured APScheduler in `scheduler.py` polling every 60s and managed in `main.py` lifespan.
- Implemented `GET /api/alerts` with regional/severity filtering and `POST /api/admin/simulate/{scenario}` for drill scenario injection.
- Exposed `alert_to_ingest_lag_seconds`, `fetch_latency_ms`, and `active_alerts_count` in `GET /health`.
### 2026-09-21 - Prompt 2 Fix: Docker Fixture Ingestion
- Updated `docker-compose.yml` to mount `./data:/data` in addition to `./data:/app/data`, ensuring `/data/fixtures/cap` and `/data/fixtures/open_meteo` are accessible inside the container.
- Updated `sachet_client.py` and `open_meteo.py` to check candidates (`/data/fixtures`, `/app/data/fixtures`, and project root).
- Rebuilt backend container and verified fixtures exist at `/data/fixtures/cap` and `/data/fixtures/open_meteo`.
- Ran `python -m pytest backend/tests` (29 passed).
- Verified `GET /api/alerts?state=Kerala` returns the Kerala flood fixture.
- Verified `POST /api/admin/simulate/kerala_flood` successfully injects simulated drill alert.


