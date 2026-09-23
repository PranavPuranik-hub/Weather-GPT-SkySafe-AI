#!/usr/bin/env python3
"""
make demo — SkySafe AI one-command demo launcher.

Steps:
1. Verify backend is running (or start it)
2. Reset demo-specific data safely (no Git files, no real user data deleted)
3. Preload the odisha_cyclone scenario
4. Open three browser views (citizen/chat, command, SMS/lab)
5. Print the 5-minute demo guide

Run with: make demo
Or directly: python scripts/demo.py
"""
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess
import webbrowser

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

VIEWS = [
    f"{FRONTEND_URL}/chat",
    f"{FRONTEND_URL}/command",
    f"{FRONTEND_URL}/lab",
]


def check_backend() -> bool:
    try:
        with urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=5) as r:
            data = json.loads(r.read())
            return data.get("status") in ("healthy", "degraded")
    except Exception:
        return False


def reset_demo_data():
    """Reset Ward 7 state and clear demo reports via the simulation endpoint.
    Only clears simulation-created data — never Git files or real user data.
    """
    payload = json.dumps({"ward_id": "Ward 7", "count": 0, "text": ""}).encode()
    req = urllib.request.Request(
        f"{BACKEND_URL}/api/reports/simulate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
        print("  ✓ Demo ward state reset")
    except Exception as e:
        print(f"  ⚠ Ward reset skipped (will work anyway): {e}")


def preload_scenario():
    """Inject the odisha_cyclone scenario into the database."""
    req = urllib.request.Request(
        f"{BACKEND_URL}/api/admin/simulate/odisha_cyclone",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            district = data.get("district", "Cuttack")
            print(f"  ✓ Cyclone scenario loaded → district: {district}")
    except Exception as e:
        print(f"  ⚠ Scenario preload failed: {e}")
        print("    You can trigger it manually via the Lab tab or curl.")


def open_browser_views():
    print("\n📱 Opening browser views…")
    for url in VIEWS:
        webbrowser.open(url)
        time.sleep(0.5)
    print("  ✓ Tabs opened: /chat · /command · /lab")


def print_guide():
    guide = """
╔══════════════════════════════════════════════════════════════════════════╗
║              SkySafe AI — 5-Minute Demo Guide                           ║
╚══════════════════════════════════════════════════════════════════════════╝

  0:00  Cyclone alert arrives
        → Lab tab: click ▶ Play (odisha_cyclone already loaded)

  0:30  Fisherman receives 30-second Odia voice note
        → Chat tab: Dev Panel → Simulate Alert → Submit

  1:00  Open Verified Claim Ledger
        → Click the ✅ badge in the chat bubble

  1:30  Break-it Panel: inject bad LLM
        → Lab → Break-it Panel → enable "Misbehaving LLM" → Submit

  2:15  Citizen reports arrive (Ward 7)
        → Chat → Dev Panel → Trigger Simulation

  2:45  PREDICTED → CONFIRMED on officer map
        → Command tab → watch Ward 7 marker change colour

  3:15  Resource allocation + Why Ledger
        → Command → click top recommendation → Why drawer opens

  4:00  Disconnect internet / toggle Source Outage
        → Lab → Source Outage → ON

  4:20  PWA + SMS continue working
        → Chat: shows offline banner, still delivers cached info

  4:40  Live Metrics page
        → Lab → 📊 Live Metrics

  5:00  Evidence Report export
        → Lab → 📄 Evidence Report (opens HTML export)

─────────────────────────────────────────────────────────────────────────
Fallbacks:
  LLM unavailable    → LLM_PROVIDER=null (template client, already set)
  TTS unavailable    → show text script
  Twilio unavailable → SMS simulator at /lab (already local)
  Wi-Fi failure      → everything runs 100% local (docker / fixtures)
─────────────────────────────────────────────────────────────────────────
Docs:  docs/DEMO.md   (full script)
       docs/SECURITY.md
       http://localhost:8000/docs  (Swagger UI)
"""
    print(guide)


def main():
    print("\n🌩️  SkySafe AI — Demo Setup\n")

    print("1/4 Checking backend…")
    if not check_backend():
        print("  ✗ Backend not running. Starting…")
        print("  → Run `make up` in a separate terminal, then `make demo` again.")
        sys.exit(1)
    print("  ✓ Backend healthy")

    print("\n2/4 Resetting demo data…")
    reset_demo_data()

    print("\n3/4 Preloading cyclone scenario…")
    preload_scenario()

    print("\n4/4 Opening browser tabs…")
    open_browser_views()

    print_guide()
    print("🚀  Demo is ready. Follow the guide above.\n")


if __name__ == "__main__":
    main()
