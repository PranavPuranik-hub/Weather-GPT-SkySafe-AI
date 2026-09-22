# SkySafe AI 🌩️ Shielding Communities with Action Intelligence

> **SIH 2026 Problem SIH26068**: *WeatherGPT: Conversational AI for Weather Forecasting, Alerts and Climate Information (Disaster Management Theme)*

**SkySafe AI** turns official government weather warnings (NDMA SACHET / IMD CAP format) into simple, life-saving, multilingual voice/SMS actions for citizens, and gives officials a live decision dashboard with prioritized resource allocation.

---

## ⚡ Quick Start

```bash
# 1. Copy environment configuration
cp .env.example .env

# 2. Spin up containers (Backend, Frontend, Postgres/PostGIS)
make up

# 3. Check backend health endpoint
curl http://localhost:8000/health

# 4. Access Frontend (PWA)
# Citizen View: http://localhost:3000/citizen
# Command Dashboard: http://localhost:3000/dashboard
```

---

## 🏗️ Monorepo Layout

```text
.
├── backend/            # FastAPI app ("app")
│   └── app/
│       ├── api/        # REST controllers & /health route
│       ├── core/       # Pydantic settings & DB connection
│       ├── ingest/     # CAP format, SACHET, Open-Meteo ingestion
│       ├── grounding/  # FactSheet & GroundingValidator logic
│       ├── agent/      # Pluggable LLM orchestrator
│       ├── i18n/       # Multilingual translations
│       ├── voice/      # TTS/STT processing
│       ├── channels/   # Twilio/SMS/WhatsApp integration
│       ├── dashboard/  # Official decision matrix logic
│       ├── optimizer/  # Resource allocation solver
│       ├── climate/    # Long-term climate info
│       ├── reports/    # Automated bulletin generator
│       ├── models/     # SQLAlchemy/PostGIS schemas
│       └── tests/      # Pytest suite (100% module coverage)
├── frontend/           # Next.js 14 PWA with Tailwind & TS
├── data/               # Fixtures, gazetteer, action library, geojson
├── docs/               # Architecture progress & decisions log
├── scripts/            # Database seeding & demo execution scripts
├── docker-compose.yml  # Container orchestration
└── Makefile            # Common management commands
```

---

## ⚙️ Key Environment Variables

| Variable | Description | Options / Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostGIS / SQLite Connection URI | `postgresql://app:app@postgres:5432/app` |
| `LLM_PROVIDER` | Active LLM Backend Driver | `ollama` \| `gemini` \| `groq` \| `null` |
| `MODE` | Operating mode | `live` \| `fixtures` |
| `DEMO_DISTRICT`| Default demo district | `Cuttack` |

---

## 🧪 Testing

Run backend tests locally:
```bash
make test
```
