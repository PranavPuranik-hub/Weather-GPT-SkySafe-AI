# SkySafe AI - Architecture & Design Decisions

## Record of Decisions

### ADR 001: SQLite Fallback for Backend Testing
- **Context**: Unit tests need to run fast and without mandatory live database infrastructure during CI or offline development.
- **Decision**: Use SQLite in-memory database as default fallback when `DATABASE_URL` is not provided or during test executions. Postgres/PostGIS will be used in containerized/production environments.
- **Consequences**: Fast unit tests, zero configuration required to run `pytest`.

### ADR 002: Modular Package Architecture (`skysafe/*`)
- **Context**: The backend needs clear boundaries between ingestion, grounding, agent logic, i18n, voice, channels, and optimization.
- **Decision**: Organize backend into 13 explicit subpackages: `api`, `core`, `ingest`, `grounding`, `agent`, `i18n`, `voice`, `channels`, `dashboard`, `optimizer`, `climate`, `reports`, `models`.
- **Consequences**: High modularity, test isolation, strict responsibilities.

### ADR 003: PWA Manifest & Service Worker Strategy
- **Context**: UX requirement for Rs 5,000 low-cost Android phones with spotty internet connectivity.
- **Decision**: Next.js App Router with custom web manifest (`public/manifest.json`) and service worker (`public/sw.js`) for offline asset caching and low bandwidth resilience.
- **Consequences**: Offline capability for critical action advisories.
