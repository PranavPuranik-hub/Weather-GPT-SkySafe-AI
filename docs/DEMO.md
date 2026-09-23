# DEMO.md — SkySafe AI 5-Minute Scripted Demo

> **SIH 2026 · SIH26068** — Demo for judges/evaluators  
> **Total runtime**: 5 minutes  
> **Prerequisite**: `make demo` (resets data, starts services, preloads cyclone scenario)

---

## Pre-Demo Checklist (5 minutes before)

- [ ] `make demo` completed successfully (green output)
- [ ] Backend running: `curl http://localhost:8000/health` → `"status": "healthy"`
- [ ] Frontend running: http://localhost:3000 loads in browser
- [ ] Three browser tabs open:
  1. **Tab 1**: http://localhost:3000/chat (Citizen view)
  2. **Tab 2**: http://localhost:3000/command (Officer command center)
  3. **Tab 3**: http://localhost:3000/lab (Lab + evaluation)
- [ ] Projector/screen sharing ready on **Tab 1**

---

## Demo Script

### **0:00 — Cyclone Alert Arrives**

> *"Imagine it's 2 AM and a CAP-format cyclone alert just arrived from NDMA SACHET."*

**Action**: In the Lab tab → Scenario Replay → select `odisha_cyclone` → click **▶ Play**.

**Expected**: Clock starts ticking. The system ingests the alert and processes it through the grounding pipeline.

**Backup**: If Lab SSE doesn't connect → call directly:
```bash
curl -X POST http://localhost:8000/api/admin/simulate/odisha_cyclone \
  -H "Content-Type: application/json" \
  -d "{}"
```

---

### **0:30 — Fisherman Receives 30-Second Odia Voice Note**

> *"Our system automatically dispatches a 30-second voice note to the fisherman in his language."*

**Action**: In Chat tab:
1. Click **⚙ Dev Panel** → **Simulate Alert** → select `odisha_cyclone` → click **Simulate**.
2. Wait for response to appear with the 🔊 audio player.
3. Click play on the audio note.

**Expected**: Odia/Hindi voice note plays; text message shows below with ✅ Claim Ledger badge.

**Backup**: If audio doesn't play → show the text script. Explain TTS is optional; text delivery always works.

---

### **1:00 — Open the Verified Claim Ledger**

> *"Every number you see here is traceable to an official NDMA SACHET source."*

**Action**: Click the **🔍 Claim Ledger** button (green badge) in the chat bubble.

**Expected**: Side drawer opens showing each claim (event type, wind speed, onset time) with its source fact ID and ✅ VERIFIED status.

**Talking points**:
- "Wind speed 120 kmh — sourced from SACHET CAP field F2."
- "LLM cannot invent numbers. If it tries, the validator blocks it."
- "If validation fails, the system falls back to a deterministic template — no hallucination ever reaches the citizen."

---

### **1:30 — Break-it Panel: Injecting a Bad LLM**

> *"We deliberately injected a misbehaving LLM that claims wind speed is 200 kmh."*

**Action**: Switch to Lab tab → click **⚡ Break-it Panel**.
1. Type: `"The wind will reach 200 kmh and destroy everything."`
2. Toggle **Inject Misbehaving LLM** → ON.
3. Click **Submit to Validator**.

**Expected**:
- Red banner: "⛔ Hallucination DETECTED — Validator Blocked Response".
- Path shown: `misbehaving_llm → template_fallback`.
- Final response shown to citizen contains no "200 kmh".

**Talking points**: "This is the single canonical adversarial LLM client. The validator always wins."

---

### **2:15 — Citizen Reports Arrive**

> *"Now citizens are reporting flooding in Ward 7."*

**Action**: In Chat tab → **Dev Panel** → **Trigger Simulation** (or run):
```bash
curl -X POST http://localhost:8000/api/reports/simulate \
  -H "Content-Type: application/json" \
  -d '{"ward_id": "Ward 7", "count": 5, "text": "Water entered my home"}'
```

**Expected**: 5 reports created. Ward 7 transitions from `PREDICTED → REPORTED`.

---

### **2:45 — PREDICTED → CONFIRMED on Officer Map**

> *"The system auto-advances to CONFIRMED after 5 independent reports from different phones."*

**Action**: Switch to Command tab. Watch the Ward 7 marker on the Leaflet map.

**Expected**: Ward 7 marker changes from yellow (PREDICTED) → orange (REPORTED) → red (CONFIRMED).

**Talking points**: "Zero-Trust Verification — we never accept a single report. 5 independent hashes required."

---

### **3:15 — Optimizer Recommends Resource Allocation with Why Ledger**

> *"The decision engine has already ranked all wards by risk and allocated resources."*

**Action**: In Command tab → scroll down to **Recommended Actions** list.
Click on the top recommendation (e.g., "1. Send 4 pumps from Depot B to Ward 7").

**Expected**: Why Ledger drawer opens showing:
- Risk score (0–100) with contributing factors
- Each factor's weight and raw value from the database
- Source annotation (e.g., "low_lying_score: 0.9 → ward_info table")

**Talking points**: "Every number in this recommendation traces to the database. No invented scores."

---

### **4:00 — Disconnect Internet**

> *"Now I'll simulate a complete internet outage."*

**Action**: Toggle **Source Outage** in Lab tab → ON (or disconnect Wi-Fi).

**Expected**: Lab shows "⚠️ OUTAGE ACTIVE". Ingest cycle logs a `SourceUnavailableError`.

---

### **4:20 — PWA + SMS Continue Working**

> *"Citizens don't notice. The app still works from cache."*

**Action**: Switch to Chat tab. Send a new message. Check SMS Simulator in Lab.

**Expected**:
- Chat tab shows "You are offline" banner but still delivers cached alert info.
- SMS simulator still accepts and parses replies (no live feed needed).

**Talking points**: "Service Worker caches the app shell and last alerts. Offline reports queue in IndexedDB and sync when connection returns."

---

### **4:40 — Live Metrics Page**

> *"Every metric you see comes directly from the database. Nothing is hardcoded."*

**Action**: Click **📊 Live Metrics** in the Lab tab.

**Expected**: Metrics page shows alert counts, ingest lag p50/p95, LLM path breakdown, language coverage — all sourced from DB queries.

---

### **5:00 — Final Evidence Report**

> *"For the judges: here is a self-contained HTML evidence export."*

**Action**: Click **📄 Evidence Report** button in Lab → opens in new tab.

**Expected**: Self-contained HTML report showing all metrics with source annotations. No hardcoded values.

---

## Fallback Plans

### Venue Wi-Fi Fails
→ Laptop already runs everything locally (Docker). Demo is completely offline-capable in `MODE=fixtures`.

### Live Feed Outage
→ `MODE=fixtures` (default) uses local XML fixtures in `data/`. No live feed needed.

### LLM Unavailable (quota / no key)
→ `LLM_PROVIDER=null` (default): TemplateClient handles all generation deterministically. Demo fully functional.

### TTS Unavailable
→ Show text message instead. Explain audio is optional and text delivery always works.

### Twilio Unavailable
→ `TWILIO_ENABLED=false` (default): SMS simulator in `/lab/sms` demonstrates the full flow locally.

### Lab SSE Disconnects
→ Use `curl` commands shown in each section above as backup.

---

## Backup curl Commands

```bash
# Simulate cyclone scenario
curl -X POST http://localhost:8000/api/admin/simulate/odisha_cyclone

# Create 5 citizen reports in Ward 7
curl -X POST http://localhost:8000/api/reports/simulate \
  -H "Content-Type: application/json" \
  -d '{"ward_id": "Ward 7", "count": 5, "text": "Water entered my home"}'

# Get ward states
curl http://localhost:8000/api/reports/wards

# Get risk scores + allocation
curl http://localhost:8000/api/decision/score

# Health check
curl http://localhost:8000/health

# Evidence report
curl http://localhost:8000/api/eval/report > evidence.html
```

### Note on Weather Data Caching
The Open-Meteo API integration uses a standard 15-minute in-memory TTL cache. This is an intentional design choice to prevent rate-limiting on free-tier APIs during the demo and in production. If you query the weather multiple times within 15 minutes, the Claim Ledger will show "Open-Meteo Forecast" but the data is served instantly from the local cache. If the live network fails entirely, it falls back to the stale cache, and finally to offline JSON fixtures.
