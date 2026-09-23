# RESILIENCE.md — SkySafe AI Graceful Degradation Runbook

> **Project**: SkySafe AI · SIH26068 WeatherGPT  
> **Last updated**: 2026-09-23

---

## Design Principle

Every degradation path must produce a graceful, citizen-visible fallback message — never a raw exception, stack trace, or HTTP 500.

---

## Degradation Paths

### 1. Live Feed Unavailable (SACHET / IMD Down)

**What happens:**
- `ingest_service.ingest_cycle()` catches the network exception internally.
- Falls back to cached alerts already in the database.
- If DB is also empty: fixture files in `data/*.xml` are loaded.
- Health endpoint returns `{"status": "degraded", "last_sachet_fetch": <last_known>}`.

**Citizen behavior:** Alerts continue to be served from cache. No raw error shown.

**Lab simulation:** `POST /api/eval/outage {"enabled": true}` triggers `SourceUnavailableError` in `ingest_cycle`.

**Automated test:** `test_resilience.py::test_ingest_sachet_failure_no_crash`

---

### 2. Internet Loss (Full Offline)

**What happens:**
- PWA Service Worker (`frontend/public/sw.js`) serves the app shell from `skysafe-v1` cache.
- Outgoing reports are queued in IndexedDB `outbox` and replayed when connection restores.
- Backend in `MODE=fixtures` serves fixture alerts without any network.

**Citizen behavior:** Chat page loads; last known alert shown; "You are offline" banner displayed; reports can still be submitted and will sync later.

**Lab simulation:** Disconnect Wi-Fi; visit `/chat` — banner appears, cached content loads.

**Automated test:** `test_resilience.py::test_fixtures_mode_serves_alerts` (Python); PWA offline behavior verified via service worker (`sw.js`).

---

### 3. LLM Quota Exhausted

**What happens:**
1. `generate_with_fallback()` tries primary LLM → catches exception.
2. If configured, tries Ollama → catches exception.
3. Falls back to `TemplateClient` (always succeeds, no network needed).
4. `compose_message()` returns `path_used="template_fallback"`.
5. Citizen receives a deterministic, validator-approved response.

**Citizen behavior:** Receives a safe, grounded template message. No raw error. Response may be less personalized but always accurate.

**Lab simulation:** Set `LLM_PROVIDER=null` (default for demo/tests).

**Automated test:** `test_resilience.py::test_llm_failure_falls_back_to_template`, `test_resilience.py::test_chat_endpoint_llm_failure_no_500`

---

### 4. TTS / Voice Synthesis Unavailable

**What happens:**
- `voice_synthesizer.synthesize()` is wrapped in try/except inside `deliver_broadcast()`.
- On failure: `audio_url` is `None`, `duration_sec` is `0.0`.
- Text message and claim ledger are still delivered normally.

**Citizen behavior:** Receives text alert without audio attachment. No error shown.

**Automated test:** `test_resilience.py::test_tts_failure_no_crash`

---

### 5. Database Slow / Temporarily Unavailable

**What happens:**
- `check_db_health()` returns `False`.
- Health endpoint returns `{"status": "degraded", "database": "disconnected"}` — still HTTP 200.
- Endpoints that require DB return a user-friendly 503 (via FastAPI `Depends(get_db)` failure handler).

**Citizen behavior:** Health check shows degraded; citizen chat returns a fallback message or 503 — never a raw stack trace.

**Automated test:** `test_resilience.py::test_health_degraded_on_db_failure`

---

### 6. Twilio / WhatsApp Unavailable

**What happens:**
- `TWILIO_ENABLED=false` (default): `send_twilio_message()` returns `True` in simulation mode; no real network call.
- `TWILIO_ENABLED=true` + failure: logs the error, returns `False`; no exception propagated.

**Citizen behavior:** SMS/WhatsApp delivery silently fails; system does not crash; operator sees log warning.

**Documentation:** `docs/DEMO.md` includes Twilio fallback plan.

---

## Health Endpoint

```
GET /health
```

Returns:
```json
{
  "status": "healthy | degraded",
  "database": "connected | disconnected",
  "last_sachet_fetch": "2026-09-23T05:30:00Z",
  "alert_to_ingest_lag_seconds": 12.4,
  "active_alerts_count": 3,
  "llm_provider": "null",
  "mode": "fixtures"
}
```

---

## Structured Logging

All application logging uses `logging.getLogger("app.*")` with:
- JSON-compatible structured format (module, level, message).
- `PIIRedactingFilter` strips phone numbers and email addresses from all records before output.
- No raw user messages stored — only intent classifications and alert IDs.
