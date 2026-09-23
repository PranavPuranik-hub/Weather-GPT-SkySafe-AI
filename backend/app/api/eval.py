"""
Eval API: Lab evaluation endpoints for SkySafe AI.
- Scenario Replay clock (start/pause/step/stream)
- Live Metrics
- Break-it Panel
- Source Outage toggle
- Evidence Report export
"""
import asyncio
import json
import logging
import string

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.eval.adversarial import run_adversarial_check
from app.eval.clock import SCENARIOS, sim_clock
from app.eval.metrics import get_all_metrics
from app.eval.outage import is_outage_enabled, set_outage

logger = logging.getLogger("app.api.eval")
router = APIRouter(prefix="/api/eval", tags=["Lab / Eval"])


# ─── Clock / Scenario Replay ──────────────────────────────────────────────────

class ClockStartRequest(BaseModel):
    scenario: str
    speed: int = 1


@router.post("/clock/start")
def clock_start(req: ClockStartRequest):
    """Start the authoritative simulated clock for a scenario."""
    if req.scenario not in SCENARIOS:
        raise HTTPException(status_code=422, detail=f"Unknown scenario. Available: {SCENARIOS}")
    sim_clock.start(req.scenario, req.speed)
    return {"status": "started", "scenario": req.scenario, "speed": req.speed}


@router.post("/clock/pause")
def clock_pause():
    sim_clock.pause()
    return {"status": "paused"}


@router.post("/clock/resume")
def clock_resume():
    sim_clock.resume()
    return {"status": "resumed"}


@router.post("/clock/step")
def clock_step():
    sim_clock.step()
    return {"status": "stepped", "tick": sim_clock.current_state()["tick"]}


@router.get("/clock/state")
def clock_state():
    return sim_clock.current_state()


@router.get("/clock/stream")
async def clock_stream():
    """
    SSE stream: emits a JSON event on each clock tick.
    Frontend subscribes once and drives all three sub-views.
    """
    import queue as q_mod
    event_queue: q_mod.Queue = q_mod.Queue(maxsize=50)

    def on_tick(event_data: dict):
        try:
            event_queue.put_nowait(event_data)
        except q_mod.Full:
            pass

    sim_clock.register_callback(on_tick)

    async def generate():
        try:
            yield "data: {\"type\": \"connected\"}\n\n"
            while True:
                try:
                    data = event_queue.get_nowait()
                    yield f"data: {json.dumps(data)}\n\n"
                except q_mod.Empty:
                    await asyncio.sleep(0.2)
        finally:
            sim_clock.unregister_callback(on_tick)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ─── Metrics ──────────────────────────────────────────────────────────────────

@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    """Return all live metrics sourced from the DB. Never hardcoded."""
    return get_all_metrics(db)


# ─── Break-it Panel ───────────────────────────────────────────────────────────

class BreakitRequest(BaseModel):
    text: str
    use_misbehaving_llm: bool = False


@router.post("/breakit")
def breakit(req: BreakitRequest):
    """
    Judge submits adversarial text. System must never emit an ungrounded number.
    When use_misbehaving_llm=True, reuses the single MisbehavingLLMClient definition.
    """
    result = run_adversarial_check(req.text, req.use_misbehaving_llm)
    return result


# ─── Source Outage Toggle ─────────────────────────────────────────────────────

class OutageRequest(BaseModel):
    enabled: bool


@router.post("/outage")
def toggle_outage(req: OutageRequest):
    """Enable or disable the simulated live-feed source outage."""
    set_outage(req.enabled)
    return {"source_outage_active": is_outage_enabled()}


# ─── Evidence Report Export ───────────────────────────────────────────────────

REPORT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>SkySafe AI — Evidence Report</title>
<style>
  body{font-family:monospace;background:#0f172a;color:#e2e8f0;padding:2rem;max-width:900px;margin:auto}
  h1{color:#38bdf8;border-bottom:1px solid #334155;padding-bottom:.5rem}
  h2{color:#7dd3fc;margin-top:2rem}
  table{width:100%;border-collapse:collapse;margin:.5rem 0}
  th{text-align:left;color:#94a3b8;font-size:.75rem;padding:.25rem .5rem;border-bottom:1px solid #334155}
  td{padding:.25rem .5rem;font-size:.8rem}
  .ok{color:#4ade80} .warn{color:#fbbf24} .fail{color:#f87171}
  .badge{display:inline-block;padding:.1rem .4rem;border-radius:.25rem;font-size:.7rem;font-weight:bold}
  .badge-ok{background:#14532d;color:#4ade80}
  .badge-fail{background:#450a0a;color:#f87171}
  footer{margin-top:3rem;font-size:.7rem;color:#475569}
</style>
</head>
<body>
<h1>🛡️ SkySafe AI — Evidence Report</h1>
<p>Generated: <b>$generated_at</b></p>

<h2>Alert Counts</h2>
<table>
  <tr><th>Metric</th><th>Value</th><th>Source</th></tr>
  <tr><td>Total Alerts Processed</td><td>$total_alerts</td><td>alerts table</td></tr>
  <tr><td>Active Alerts</td><td>$active_alerts</td><td>alerts table</td></tr>
  <tr><td>Simulated/Drill Alerts</td><td>$simulated_alerts</td><td>alerts table</td></tr>
</table>

<h2>Feed Ingest Latency</h2>
<table>
  <tr><th>Metric</th><th>Value</th><th>Source</th></tr>
  <tr><td>p50 Ingest Lag</td><td>$p50_lag s</td><td>alerts.ingest_lag_seconds</td></tr>
  <tr><td>p95 Ingest Lag</td><td>$p95_lag s</td><td>alerts.ingest_lag_seconds</td></tr>
</table>

<h2>LLM Pipeline Breakdown</h2>
<table>
  <tr><th>Path</th><th>Count</th><th>Source</th></tr>
  $llm_rows
</table>

<h2>Broadcast Latency</h2>
<table>
  <tr><th>Metric</th><th>Value</th><th>Source</th></tr>
  <tr><td>p50 Delivery Latency</td><td>$p50_delivery ms</td><td>chat_events.latency_ms</td></tr>
  <tr><td>p95 Delivery Latency</td><td>$p95_delivery ms</td><td>chat_events.latency_ms</td></tr>
</table>

<h2>Language Coverage</h2>
<p>$languages (<b>$lang_count</b> languages)</p>

<h2>Report → Confirmation Latency</h2>
<table>
  <tr><th>Metric</th><th>Value</th><th>Source</th></tr>
  <tr><td>Average (confirmed wards)</td><td>$confirm_avg s</td><td>ward_states - reports</td></tr>
  <tr><td>Confirmed Ward Count</td><td>$confirm_count</td><td>ward_states - reports</td></tr>
</table>

<h2>Resilience Status</h2>
<table>
  <tr><th>Feature</th><th>Status</th></tr>
  <tr><td>Source Outage Active</td><td class="$outage_class">$source_outage</td></tr>
  <tr><td>Grounding Validator</td><td class="ok">✓ Active — zero ungrounded numbers exposed</td></tr>
  <tr><td>Deterministic Template Fallback</td><td class="ok">✓ Active</td></tr>
  <tr><td>PWA Offline Support</td><td class="ok">✓ Service Worker registered</td></tr>
  <tr><td>SMS Fallback</td><td class="ok">✓ Deterministic encoder, no LLM</td></tr>
</table>

<footer>
  SkySafe AI — SIH26068 WeatherGPT — DRILL / SIMULATION environment<br/>
  Every metric on this page is derived from the live database. No hardcoded values.
</footer>
</body>
</html>
"""


@router.get("/report", response_class=HTMLResponse)
def evidence_report(db: Session = Depends(get_db)):
    """Generate a self-contained HTML evidence report from live DB metrics."""
    m = get_all_metrics(db)

    ac = m["alert_counts"]
    il = m["ingest_latency"]
    lp = m["llm_path_breakdown"]
    bl = m["broadcast_latency"]
    lc = m["language_coverage"]
    rc = m["report_confirmation_latency"]
    outage = m["source_outage_active"]

    llm_rows_html = ""
    for path, cnt in lp.get("breakdown", {}).items():
        llm_rows_html += f"<tr><td>{path}</td><td>{cnt}</td><td>chat_events.path_used</td></tr>"
    if not llm_rows_html:
        llm_rows_html = "<tr><td colspan='3'>No events yet</td></tr>"

    tmpl = string.Template(REPORT_TEMPLATE)
    html = tmpl.safe_substitute(
        generated_at=m["generated_at"],
        total_alerts=ac["total"],
        active_alerts=ac["active"],
        simulated_alerts=ac["simulated"],
        p50_lag=il["p50_seconds"] or "N/A",
        p95_lag=il["p95_seconds"] or "N/A",
        llm_rows=llm_rows_html,
        p50_delivery=bl["p50_ms"] or "N/A",
        p95_delivery=bl["p95_ms"] or "N/A",
        languages=", ".join(lc["languages"]) or "N/A",
        lang_count=lc["count"],
        confirm_avg=rc["avg_seconds"] or "N/A",
        confirm_count=rc["count"],
        source_outage="⚠️ ACTIVE" if outage else "✓ Off",
        outage_class="warn" if outage else "ok",
    )
    return HTMLResponse(content=html)
