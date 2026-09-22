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
- Configured FastAPI application `app` with pydantic-settings and `/health` endpoint.
- Built Next.js 14 PWA placeholder with mobile-first landing page and route links for Citizen view and Command dashboard.
- Configured PostgreSQL / PostGIS container service, Makefile targets (`up`, `down`, `test`, `lint`, `seed`, `demo`), and environment variables template.
### 2026-09-21 - Prompt 1 Fix: PostgreSQL Driver Dependency
- Added `psycopg2-binary>=2.9.9` dependency to `backend/requirements.txt` and `backend/pyproject.toml`.
- Added unit test `test_postgres_driver_import` to verify `postgresql://` URI engine initialization.
### 2026-09-21 - Prompt 1 Fix: /health Routing Resolution
- Resolved FastAPI empty path/prefix collision in `app/api/health.py` by configuring explicit `/health` and `/health/` decorators on `health_router`.
- Verified GET `/health` and GET `/health/` return HTTP 200 with required JSON payload keys (`status`, `database`, `last_sachet_fetch`, `last_open_meteo_fetch`, `llm_provider`, `mode`).
### 2026-09-21 - Prompt 1 Fix: Docker Port Binding
- Updated `docker-compose.yml` backend service port mapping from `"8000:8000"` to `"0.0.0.0:8000:8000"`.
- Explicitly configured host binding so container port 8000 maps to `0.0.0.0:8000->8000/tcp`.
- All 16 backend unit tests pass.

### 2026-09-21 - Ingestion Layer (`app/ingest`)
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

### 2026-09-22 - Prompt 3: Zero-LLM Action Intelligence & Grounding Layer (`app/core`)
- Built immutable `FactSheet` builder (`app/core/factsheet.py`) extracting facts with stable IDs (`F1`, `F2`...), regex number/unit extraction for wind, waves, rainfall, temperature with character spans (`source_span`).
- Built `GradeEngine` (`app/core/grade.py`) mapping severity, urgency, certainty, and color codes to Grades A, B, C, D with mandatory Grade A + Safety Check rule for Extreme severity or Red alerts.
- Authored declarative YAML rule files for 5 hazards x 5 personas across all 4 grades in `app/core/rules/` (`cyclone.yaml`, `heavy_rain_flood.yaml`, `heatwave.yaml`, `thunderstorm_lightning.yaml`, `storm_surge_high_waves.yaml`).
- Implemented `RuleEngine` (`app/core/rule_engine.py`) with Fisherman SAFE/UNSAFE threshold evaluation (>= 2.5m waves or >= 45 km/h wind) and template rendering with fact ID traceability (`why`).
- Implemented `ActionPlan` model and builder (`app/core/action_plan.py`).
- Built CLI demo simulator (`app/core/demo.py`) supporting `--scenario cyclone`, `--scenario flood`, and `--scenario heatwave`.
- Created comprehensive unit test suite in `backend/tests/core/` (`test_factsheet.py`, `test_grade.py`, `test_rules.py`, `test_fisherman_rule.py`, `test_demo.py`).
- Created root `app` package layout enabling `python -m app.core.demo --scenario cyclone` directly from the repository root.
### 2026-09-22 - Prompt 4: Grounded LLM Generation & Adversarial Grounding Validator
- Built pluggable LLM layer `app/llm` (Ollama, Gemini, TemplateClient) with deterministic provider fallback chain and Gemini as default.
- Implemented deterministic Grounding Validator in `app/validator` with Indic numeral normalizer, unit fuzzy-matching, action negation preservation, and hallucination detection.
- Built generation pipeline `app/pipeline/composer.py` (`generate -> validate -> retry (max 2) -> fallback`).
- Implemented `POST /api/compose` endpoint returning grounded plain-language text, voice script, and `ClaimLedger`.
- Built 52-case adversarial test suite `tests/validator/test_adversarial.py` achieving 100% catch rate via `python -m app.validator.report`.

### 2026-09-22 - Prompt 5: Multilingual Language Registry & Voice Notes
- Configured 17-language registry in `backend/app/lang/languages.yaml` with language metadata, scripts, RTL flags, TTS voices, and `verified` filtering (`get_verified_languages()` shown by default in UI).
- Implemented native Indic digit rendering in `app/lang/digits.py` for target scripts (Devanagari, Bengali, Odia, Telugu, Tamil, Marathi, Gujarati, etc.).
- Implemented telecom-compliant SMS budgeting in `app/lang/sms.py` (GSM-7 <= 160 chars, Unicode <= 201 chars / <= 3 segments).
- Built deterministic per-language template packs in `app/lang/templates/pack.py` with localized templates and fact slots.
- Implemented `TranslationService` in `app/lang/translator.py` with provider hierarchy: Sarvam AI (if API key) -> Deterministic Template Packs -> English fallback.
- Enforced strict Grounding Validation on all translated text: numeric tokens (normalized across Indic digits) and place names must match source FactSheet; ungrounded/altered translations are rejected.
- Implemented Voice synthesis service in `app/voice/synthesizer.py` with TTS chain: Sarvam TTS -> Edge-TTS -> gTTS -> browser speechSynthesis fallback.
- Added emergency broadcast two-tone alert chime in `app/voice/chime.py` and voice note caching by SHA256(text, lang, voice) with <= 30s duration and < 200 KB size guarantee.
- Implemented API endpoints in `app/api/voice.py`:
  - `POST /api/voice`: generates localized, grounded voice notes returning audio URL, transcript, SMS text, and ClaimLedger.
  - `GET /api/voice/audio/{filename}`: serves cached audio files.
  - `GET /api/languages`: lists verified languages (or all 17 when `?all=true`).
- Added comprehensive test suite `tests/test_lang_and_voice.py` verifying 7 languages across 3 scenarios, audio <= 30s, and proving that any translation altering a numeral is strictly rejected.
- All 225 backend unit tests passing cleanly (`pytest tests/ -q`).
- 
### 2026-09-22 - Prompt 6: Citizen Conversational AI (`/backend/app/chat` & `/frontend/src/app/chat`)
- Addressed SIH problem SIH26068 ("WeatherGPT: Conversational AI for weather forecasting, alerts and climate information"):
  - Built deterministic tool layer in `app/chat/tools.py`: `get_active_alerts`, `get_forecast`, `get_marine`, `get_climate_normals`, `nearest_shelter`, backed by curated emergency cyclone shelters registry and Open-Meteo/climatology fallbacks.
  - Implemented geocoding resolver in `app/chat/geocoding.py` with disaster-prone district registry, reverse geocoding for GPS coordinates, and India-bounded Nominatim geocoder with in-memory caching.
  - Built rule-first intent router in `app/chat/router.py` covering 9 core intents across English, Hindi, and Odia: `current_alert`, `forecast`, `safety_check`, `nearest_shelter`, `action_advice`, `climate_info`, `change_language`, `registration`, `report_incident`.
  - Implemented chat orchestration engine in `app/chat/engine.py` producing deterministic FactSheets, executing Grounding Validator to yield audit-proof `ClaimLedger`, and synthesizing voice notes.
  - Enforced strict honest fallback: out-of-scope queries clearly declare lack of official data and direct citizens to official IMD helpline (1800-180-1717 / 1077 / `https://mausam.imd.gov.in`).
  - Privacy compliance: Phone numbers stored only as irreversible SHA-256 hashes for alert subscription consent.
  - Built full API endpoints in `app/api/chat.py`: `POST /api/chat/message`, `POST /api/chat/onboard`, `POST /api/chat/report`, `POST /api/chat/simulate`.
  - Built Next.js WhatsApp-styled UI simulator in `frontend/src/app/chat/page.tsx`:
    - High-contrast, accessible design tailored for ₹5,000 Android phones.
    - Interactive onboarding modal (language selector, 5 persona icons, location/GPS detection, alert consent).
    - WhatsApp green bubbles with double checkmarks, quick-reply chip bar, Web Speech API mic button for voice transcription.
    - In-bubble voice note player with animated waveform bars and <=30s duration playback.
    - Verified Claim Ledger proof drawer (`components/ClaimLedgerDrawer.tsx`) providing sentence-level grounding audit and facts breakdown.
### 2026-09-22 - Prompt 6: Simulation Flow Debug & End-to-End Broadcast Integration
- Debugged and unified the simulation pipeline using existing Prompt 2 infrastructure without dummy or faked components:
  - Frontend `DevPanel` (`components/DevPanel.tsx`) now directly triggers `POST /api/admin/simulate/{scenario}` with query params `lang`, `persona`, and `district`.
  - Expanded `ingest_service.simulate_scenario` (`app/ingest/service.py`) with support for scenario timeline steps (`cyclone_t24`, `cyclone_t12`, `cyclone_t3`), short aliases (`cyclone`, `flood`, `heatwave`), and target district customization.
  - Implemented `deliver_broadcast` in `app/channels/broadcast.py`:
    - Constructs FactSheet and ActionPlan for the target persona.
    - Generates grounded Class-6 message via `compose_message` and `translation_service`.
    - Enforces Rule 2: `[DRILL / SIMULATION]` labels on message and voice script.
    - Synthesizes real localized voice note audio using `voice_synthesizer`.
    - Measures real dispatch latency in milliseconds (`delivery_latency_ms`), enforcing `<60s` SLA.
  - Enriched `POST /api/admin/simulate/{scenario}` to return the original simulated alert dictionary augmented with the broadcast delivery payload (`message`, `voice_script`, `audio_url`, `claim_ledger`, `delivery_latency_ms`, `quick_replies`).
  - Updated `ChatPage` (`frontend/src/app/chat/page.tsx`) to append the incoming emergency drill message, render the animated voice player, enable the ClaimLedgerDrawer proof inspection, and display the live latency timer in the dev panel.
### 2026-09-22 - Prompt 6: Geographic Coherence & Grounding Validator Audit
- Identified root cause of mismatched places (e.g., "Nagpur, Rajasthan"):
  - When a drill scenario district was selected (e.g. `Nagpur`), the fixture's default state (`Rajasthan`) was retained, producing a FactSheet with `area = Nagpur, Rajasthan`.
  - The Grounding Validator previously verified that the LLM/template did not hallucinate facts beyond the input `FactSheet`. Because `Nagpur, Rajasthan` was explicitly in the input `FactSheet`, the validator correctly reported `PASS` with zero ungrounded tokens relative to the source data.
- Implemented dual-layer Geographic Coherence protection:
  1. `app/ingest/service.py`: Added `KNOWN_DISTRICT_TO_STATE` lookup table so drill scenario simulations dynamically map districts to their authentic states (e.g., `Nagpur` -> `Maharashtra`, `Wayanad` -> `Kerala`, `Cuttack` -> `Odisha`), harmonizing `parsed["state"]`, `parsed["area_desc"]`, `parsed["headline"]`, and `parsed["description"]`.
  2. `app/validator/engine.py`: Enhanced `validate_sentence()` with an explicit Geographic Coherence audit rule. Any sentence linking a known Indian district with a conflicting state (e.g., `Nagpur, Rajasthan`) is deterministically rejected (`status = FAIL`, `reason = "Geographic discrepancy: 'Nagpur' is in 'Maharashtra', not 'Rajasthan'."`).
- Verified with 244 backend unit tests passing cleanly.

### 2026-09-22 - Prompt 6: Active Alert Pipeline Fix & Frontend CSS Restoration
- Corrected active-alert query flow:
  - Replaced ad-hoc string formatting in `app/chat/engine.py` with the full grounding pipeline: `FactSheet` -> `ActionPlan` -> `compose_message` -> `validate_payload` -> `ClaimLedger`.
  - Added strict check for `is_simulation`: `[DRILL / SIMULATION]` prefix is added if and only if the underlying alert is a simulation drill (`is_simulation == True`). Genuine warnings are never prefixed with `[DRILL]`.
  - In `app/chat/tools.py`, prioritized exact `Alert.district` matching before fallback to substring searches, and sorted actual alerts before simulation drills.
  - In `frontend/src/app/chat/page.tsx`, ensured regular chat responses have `isDrill: false` and restricted the red `EMERGENCY BROADCAST [DRILL]` header banner exclusively to incoming broadcast drills.
  - Added unit tests in `tests/test_chat.py` verifying active Wayanad alert data, `status: PASS` ledger, and absence of drill label on real alerts (all 246 backend tests pass).
- Resolved frontend CSS rendering regression:
  - Root cause: An orphan Node process on port 3000 was serving stale dev HTML while its `.next/static/css` assets had been overwritten during a concurrent build, resulting in HTTP 404 for `/_next/static/css/app/layout.css`.
  - Cleared stale `.next` cache, terminated orphan background processes on ports 3000/3001, and restarted dev server. Verified `app/layout.css` compiles via Tailwind CSS and returns HTTP 200 (37.8 KB), fully restoring WhatsApp styling, fonts, icons, and layout.
