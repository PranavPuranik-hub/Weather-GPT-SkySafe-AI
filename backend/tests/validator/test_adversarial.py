"""
Adversarial test suite for Grounding Validator.
Ensures zero hallucinations pass through the validation engine.
"""
import pytest
from app.validator.engine import validate_payload
from app.core.factsheet import FactSheet, Fact
from app.core.action_plan import ActionPlan
# Single canonical definition of the adversarial LLM — do NOT redefine here
from app.llm.misbehaving_client import MisbehavingLLMClient

# Dummy data
FACTSHEET_DATA = {
    "facts": [
        {"id": "F1", "field": "event", "value": "Cyclone"},
        {"id": "F2", "field": "wind_speed", "value": "120 kmh"},
        {"id": "F3", "field": "time", "value": "14:30"},
        {"id": "F4", "field": "location", "value": "Cuttack"}
    ]
}

ACTIONPLAN_DATA = {
    "ordered_actions": [
        {"id": "a1", "instruction": "Do not go out to sea."},
        {"id": "a2", "instruction": "Evacuate immediately."},
        {"id": "a3", "instruction": "Keep emergency kit ready."}
    ]
}

def create_payload(text: str, fact_ids: list = None, action_ids: list = None):
    return {
        "text_script_sentences": [
            {
                "text": text,
                "fact_ids": fact_ids if fact_ids is not None else ["F1", "F2", "F3", "F4"],
                "action_ids": action_ids if action_ids is not None else ["a1", "a2", "a3"]
            }
        ],
        "voice_script_sentences": []
    }

# We need 40+ adversarial cases.
# We will generate them dynamically to ensure variety.
adversarial_cases = [
    # 1. Fake Wind Speed
    ("Wind speed will reach 150 kmh.", ["F2"], []),
    ("Wind speed will reach 130 kmh.", ["F2"], []),
    # 2. Fake Time
    ("Cyclone hits at 15:30.", ["F3"], []),
    ("Cyclone hits at 14:45.", ["F3"], []),
    # 3. Fake Helpline (10 digit numbers)
    ("Call helpline at 9876543210.", [], []),
    ("Emergency number is 1234567890.", [], []),
    # 4. Dropped Negation
    ("Go out to sea.", [], ["a1"]),
    ("You should go out to sea.", [], ["a1"]),
    ("Please go out to sea now.", [], ["a1"]),
    # 5. Hindi digits for wrong number
    ("Wind speed is १५० kmh.", ["F2"], []),
    ("Time is १५:३०.", ["F3"], []),
    # 6. Unrelated place
    ("Cyclone hits Mumbai.", ["F4"], []),
    ("Evacuate Delhi.", ["F4"], []),
    ("Danger in Unknown City.", [], []),
    # 7. Invented action
    ("Board up your windows.", [], ["a1", "a2"]),
    ("Buy extra milk.", [], ["a3"]),
    # 8-40. Generating more combinations to reach 40+
]

# Let's dynamically add more variations
for speed in [100, 110, 125, 140, 160, 200, 50, 75]:
    adversarial_cases.append((f"Winds will be {speed} kmh.", ["F2"], []))
for hr in [10, 11, 12, 13, 15, 16, 17, 18, 19]:
    adversarial_cases.append((f"Expected at {hr}:30.", ["F3"], []))
for phone in ["8888888888", "9999999999", "1111111111", "5555555555"]:
    adversarial_cases.append((f"Dial {phone} for help.", [], []))
for fp in ["Atlantis", "Chennai", "Kolkata", "Bengaluru"]:
    adversarial_cases.append((f"Take shelter in {fp}.", ["F4"], []))
for neg in ["Go out to sea", "You must go out to sea", "Proceed out to sea"]:
    adversarial_cases.append((neg, [], ["a1"]))
for i_action in ["Call the police", "Hide under the bed", "Wait for the president"]:
    adversarial_cases.append((i_action, [], []))
    
# Valid cases for baseline
valid_cases = [
    ("Cyclone wind speed is 120 kmh.", ["F1", "F2"], []),
    ("At 14:30 in Cuttack.", ["F3", "F4"], []),
    ("Do not go out to sea.", [], ["a1"]),
    ("Evacuate immediately.", [], ["a2"])
]

@pytest.mark.parametrize("text,fids,aids", adversarial_cases)
def test_adversarial_rejected(text, fids, aids):
    payload = create_payload(text, fids, aids)
    ledger = validate_payload(payload, "test_alert", FACTSHEET_DATA, ACTIONPLAN_DATA)
    assert ledger.status == "FAIL", f"Adversarial case passed validation incorrectly: {text}"

@pytest.mark.parametrize("text,fids,aids", valid_cases)
def test_valid_accepted(text, fids, aids):
    payload = create_payload(text, fids, aids)
    ledger = validate_payload(payload, "test_alert", FACTSHEET_DATA, ACTIONPLAN_DATA)
    assert ledger.status == "PASS", f"Valid case failed validation incorrectly: {ledger.global_reason} | {ledger.get_violations_text()}"
