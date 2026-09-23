# SECURITY.md — SkySafe AI OWASP API Top 10 Checklist

> **Project**: SkySafe AI · SIH26068 WeatherGPT  
> **Version**: Phase C (Prompt 11 Hardening)  
> **Last updated**: 2026-09-23

---

## OWASP API Security Top 10 — Implementation Status

### API1:2023 — Broken Object Level Authorization

| Item | Implementation | Status |
|------|---------------|--------|
| Object-level authorization on all endpoints | All data access uses the shared DB session; alert lookups are by public `alert_id`; no user-private objects exposed without session | ✅ PASS |
| No user can access another user's data | No private-user data is stored (reports are anonymous hashes); no user-scoped endpoints exist | ✅ PASS |
| **Known limitation** | Session store is in-memory; no JWT/OAuth; suitable for demo; add proper auth before production | ⚠️ |

---

### API2:2023 — Broken Authentication

| Item | Implementation | Status |
|------|---------------|--------|
| Admin endpoints require demo mode | `POST /api/admin/simulate/*` is gated to `MODE=fixtures` only | ✅ PASS |
| No credentials in source code | All secrets via env vars only (`.env.example` provided, `.env` git-ignored) | ✅ PASS |
| **Known limitation** | No token-based auth on citizen endpoints — intentional for low-friction demo | ⚠️ |

---

### API3:2023 — Broken Object Property Level Authorization

| Item | Implementation | Status |
|------|---------------|--------|
| Pydantic v2 models with explicit field definitions | All request/response models use explicit `Field(...)` — no `__all__` or wildcard exposure | ✅ PASS |
| No extra fields leaked | `model_config = SettingsConfigDict(extra="ignore")` on Settings | ✅ PASS |

---

### API4:2023 — Unrestricted Resource Consumption

| Item | Implementation | Status |
|------|---------------|--------|
| Input length limits | `ChatRequest.message` ≤ 500 chars; `IncidentReportRequest.description` ≤ 1000 chars; all fields have `max_length` | ✅ PASS |
| Rate limiting | `RateLimiter(60 req / 60 s per IP)` in `app/core/security.py` | ✅ PASS |
| SMS segment limit | SMS encoder enforces 160-char (GSM-7) / 70-char (UCS-2) per segment, max 3 segments | ✅ PASS |
| Voice note limit | Voice synthesizer enforces < 30-second scripts | ✅ PASS |

---

### API5:2023 — Broken Function Level Authorization

| Item | Implementation | Status |
|------|---------------|--------|
| Simulation endpoints gated | `/api/admin/simulate/*` returns 403 in `live` mode | ✅ PASS |
| Eval/Lab endpoints | `/api/eval/*` (outage toggle, clock) are lab-only; no citizen data mutation | ✅ PASS |

---

### API6:2023 — Unrestricted Access to Sensitive Business Flows

| Item | Implementation | Status |
|------|---------------|--------|
| Report submission rate limiting | Per-IP rate limiter applies to `/api/reports` | ✅ PASS |
| Alert injection blocked in production | `MODE=live` blocks simulation endpoints | ✅ PASS |

---

### API7:2023 — Server-Side Request Forgery (SSRF)

| Item | Implementation | Status |
|------|---------------|--------|
| External URLs are hardcoded config | `SACHET_RSS_URL`, `IMD_RSS_URL` are env-var strings; user input never controls fetch targets | ✅ PASS |
| No proxy or URL-forwarding endpoints | No user-controlled HTTP request forwarding | ✅ PASS |

---

### API8:2023 — Security Misconfiguration

| Item | Implementation | Status |
|------|---------------|--------|
| CORS restricted | `ALLOWED_ORIGINS` env var; defaults to `localhost:3000,3001` only | ✅ PASS |
| No secrets in Git | `.gitignore` excludes `.env`; `.env.example` contains only placeholders | ✅ PASS |
| Structured logging | `logging.getLogger("app")` with `PIIRedactingFilter` applied | ✅ PASS |
| **Known limitation** | HTTPS not enforced at app layer — expected to run behind a reverse proxy (nginx/caddy) in production | ⚠️ |

---

### API9:2023 — Improper Inventory Management

| Item | Implementation | Status |
|------|---------------|--------|
| OpenAPI docs auto-generated | FastAPI generates `/docs` (Swagger UI) from code | ✅ PASS |
| All endpoints documented with tags | Every router uses `tags=[...]` | ✅ PASS |

---

### API10:2023 — Unsafe Consumption of APIs

| Item | Implementation | Status |
|------|---------------|--------|
| LLM output validated before exposure | `validate_payload()` called on every LLM response; validator blocks hallucinated numbers | ✅ PASS |
| External API failures caught | All `sachet_client`, `imd_client`, `voice_synthesizer` calls wrapped in try/except | ✅ PASS |
| Fixtures fallback when live feed fails | `SourceUnavailableError` triggers graceful fallback to cached DB / fixture data | ✅ PASS |

---

## Prompt-Injection Protection

**Rule**: User text **never** enters the system prompt.

Implementation path:
1. `ChatRequest.message` → Pydantic `field_validator` → `detect_prompt_injection()` → 422 if detected.
2. User message only selects an *intent* via `classify_intent()` (keyword classifier — no LLM involved).
3. LLM system prompt is a hardcoded constant (`REWORDING_SYSTEM_PROMPT` in `app/llm/prompts.py`).
4. User text only populates the constrained report pipeline (structured DB insert).

Patterns detected: `ignore previous instructions`, `system prompt`, `jailbreak`, `act as`, `bypass safety`, XML injection tags, etc. (28 patterns in `app/core/security.py`).

---

## PII Policy

- Phone numbers are **hashed (SHA-256, 32-char hex)** immediately on receipt via `hash_phone()`.
- Raw phone numbers are **never stored** in the database.
- `PIIRedactingFilter` strips 10-digit Indian phone numbers and email addresses from all log records.
- No location data beyond district/town level is stored.

---

## Environment Variables — Security-Relevant

| Variable | Required | Notes |
|----------|----------|-------|
| `GEMINI_API_KEY` | No | Demo/tests work with `LLM_PROVIDER=null` |
| `TWILIO_ACCOUNT_SID` | No | Simulated by default (`TWILIO_ENABLED=false`) |
| `TWILIO_AUTH_TOKEN` | No | Same |
| `ALLOWED_ORIGINS` | No | Defaults to localhost only |
| `DATABASE_URL` | No | Defaults to SQLite for demo |
