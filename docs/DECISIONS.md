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

### ADR 004: Ingestion Redundancy and Geometry Storage
- **Context**: Official government feeds (NDMA SACHET, IMD) may face intermittent downtime or slow responses during active cyclone/monsoon events. Tests run on SQLite where SpatiaLite is not guaranteed.
- **Decision**: Primary ingestion queries NDMA SACHET RSS, with automatic fallback and secondary redundancy from IMD RSS. Offline demo uses `/data/fixtures/cap/*.xml`. Geometry is parsed from `<polygon>` coordinates and stored as standardized GeoJSON in a `geometry` column, ensuring 100% interoperability across PostGIS in production and SQLite in automated testing.
- **Consequences**: Zero ingestion downtime, honest alert-to-ingest lag tracking, fully functional offline demo mode.

### ADR 005: Zero-LLM Grounded Action Engine
- **Context**: The action intelligence layer must provide life-saving, deterministic advice that works when LLMs are disabled or offline, without hallucination risk.
- **Decision**: Implemented `backend/app/core/` containing an immutable `FactSheet` builder (with regex span extraction for wind, waves, rainfall, and temperature), a deterministic `GradeEngine` mapping alert attributes to threat Grades A-D, declarative YAML rules for 5 hazards x 5 personas, and full `why` fact ID traceability.
- **Consequences**: 100% deterministic grounding, zero LLM dependency for core decision making, full offline capability for emergency response.
