"""
CLI Demo Executable: Simulates timeline steps for a disaster scenario and prints ActionPlan per persona.
Usage: python -m app.core.demo --scenario cyclone
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from app.core.action_plan import generate_action_plan
from app.core.factsheet import build_factsheet


def run_demo(scenario: str = "cyclone") -> None:
    """
    Execute CLI scenario demonstration across multiple timeline steps.
    """
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print(f"\n==========================================================================")
    print(f"[DEMO] SKYSAFE AI - DISASTER ACTION INTELLIGENCE CLI DEMO (ZERO-LLM)")
    print(f"[*] Scenario: {scenario.upper()} DRILL")
    print(f"==========================================================================")

    now = datetime.now(timezone.utc)
    personas = ["general", "farmer", "fisherman", "elderly_alone", "pregnant_infants"]

    if scenario.lower() == "cyclone":
        timeline_steps = [
            {
                "step": "T-24h Advisory & Watch",
                "alert": {
                    "identifier": "DRILL-CYC-T24",
                    "event": "Cyclonic Storm Watch",
                    "severity": "Moderate",
                    "urgency": "Future",
                    "certainty": "Possible",
                    "district": "Cuttack",
                    "state": "Odisha",
                    "headline": "Cyclonic depression in Bay of Bengal moving towards Odisha coast.",
                    "description": "System likely to intensify with wind speeds of 50 km/h and wave heights of 2.0 meters.",
                    "expires": (now + timedelta(hours=24)).isoformat()
                },
                "open_meteo": {
                    "hourly": {"wind_speed_10m": [45.0], "wind_gusts_10m": [58.0], "wave_height": [2.1]}
                }
            },
            {
                "step": "T-12h Warning & Preparation",
                "alert": {
                    "identifier": "DRILL-CYC-T12",
                    "event": "Severe Cyclonic Storm Warning",
                    "severity": "Severe",
                    "urgency": "Expected",
                    "certainty": "Likely",
                    "district": "Cuttack",
                    "state": "Odisha",
                    "headline": "Severe Cyclone Warning for Odisha coast near Cuttack and Puri.",
                    "description": "Gale winds of 95 km/h gusting to 120 kmph with high swell waves of 3.8 meters expected.",
                    "expires": (now + timedelta(hours=12)).isoformat()
                },
                "open_meteo": {
                    "hourly": {"wind_speed_10m": [95.0], "wind_gusts_10m": [120.0], "wave_height": [3.8]}
                }
            },
            {
                "step": "T-3h Imminent Landfall & Evacuation",
                "alert": {
                    "identifier": "DRILL-CYC-T03",
                    "event": "Very Severe Cyclonic Storm",
                    "severity": "Extreme",
                    "urgency": "Immediate",
                    "certainty": "Observed",
                    "district": "Cuttack",
                    "state": "Odisha",
                    "headline": "Red Alert: Very Severe Cyclone Landfall Imminent in Cuttack.",
                    "description": "Destructive gale winds of 145 kmh gusting to 160 kmh with tidal surge and wave heights of 5.5 m.",
                    "expires": (now + timedelta(hours=6)).isoformat()
                },
                "open_meteo": {
                    "hourly": {"wind_speed_10m": [145.0], "wind_gusts_10m": [160.0], "wave_height": [5.5]}
                }
            }
        ]
    elif "rain" in scenario.lower() or "flood" in scenario.lower():
        timeline_steps = [
            {
                "step": "T-12h Flood Watch",
                "alert": {
                    "identifier": "DRILL-FLD-T12",
                    "event": "Heavy Rain Warning",
                    "severity": "Moderate",
                    "urgency": "Expected",
                    "district": "Wayanad",
                    "state": "Kerala",
                    "headline": "Heavy rainfall alert for Wayanad district.",
                    "description": "Rainfall of 85 mm expected over 24 hours.",
                    "expires": (now + timedelta(hours=12)).isoformat()
                }
            },
            {
                "step": "T-3h Extreme Inundation",
                "alert": {
                    "identifier": "DRILL-FLD-T03",
                    "event": "Flash Flood Warning",
                    "severity": "Extreme",
                    "urgency": "Immediate",
                    "district": "Wayanad",
                    "state": "Kerala",
                    "headline": "Red Alert: Flash Floods and Inundation in Wayanad.",
                    "description": "Extremely heavy rainfall exceeding 210 mm in 24 hours.",
                    "expires": (now + timedelta(hours=6)).isoformat()
                }
            }
        ]
    else:
        timeline_steps = [
            {
                "step": "Peak Noon Heatwave Advisory",
                "alert": {
                    "identifier": "DRILL-HW-T00",
                    "event": "Severe Heatwave",
                    "severity": "Extreme",
                    "urgency": "Immediate",
                    "district": "Churu",
                    "state": "Rajasthan",
                    "headline": "Red Alert: Severe Heatwave in Churu.",
                    "description": "Maximum temperatures crossing 47 °C with severe loo wind conditions.",
                    "expires": (now + timedelta(hours=8)).isoformat()
                }
            }
        ]

    for step_data in timeline_steps:
        step_name = step_data["step"]
        alert = step_data["alert"]
        open_meteo = step_data.get("open_meteo")

        factsheet = build_factsheet(alert, open_meteo_data=open_meteo)

        print(f"\n--------------------------------------------------------------------------")
        print(f"[STEP] TIMELINE STEP: {step_name.upper()}")
        print(f"--------------------------------------------------------------------------")
        print(f"[FACTS] Headline Facts extracted for grounding:")
        for f in factsheet.facts[:5]:
            print(f"   [{f.id}] {f.field}: {f.value} (source: {f.source})")

        print(f"\n[ACTION PLANS] GENERATED ACTION PLANS PER PERSONA:")

        for persona in personas:
            plan = generate_action_plan(factsheet, persona=persona, hazard_override=scenario.lower())
            
            check_badge = " [SAFETY CHECK REQUIRED]" if plan.safety_check_required else ""
            print(f"\n   -> Persona: {persona.upper()} | Grade: {plan.grade}{check_badge}")
            print(f"      Why (Fact IDs): {plan.why}")
            for idx, act in enumerate(plan.ordered_actions, 1):
                print(f"      {idx}. [{act['id']}] {act['action']}")

    print(f"\n==========================================================================")
    print(f"[OK] Demo execution completed cleanly.")
    print(f"==========================================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="SkySafe AI Grounded Action Intelligence CLI Demo")
    parser.add_argument("--scenario", type=str, default="cyclone", help="Disaster scenario: cyclone, flood, heatwave")
    args = parser.parse_args()
    run_demo(args.scenario)


if __name__ == "__main__":
    main()
