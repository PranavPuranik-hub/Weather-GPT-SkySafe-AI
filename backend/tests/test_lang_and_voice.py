"""
Acceptance Test Suite for Multilingual Translation and Voice Services.
Verifies:
1. 17-language registry with verified filtering.
2. 7 languages x 3 scenarios: message generation, grounding validation, audio duration <= 30s.
3. Test proving translation altering a number is strictly rejected.
4. Voice API endpoints (POST /api/voice, GET /api/voice/audio, GET /api/languages).
5. SMS budgeting (<= 160 chars GSM-7; <= 3 Unicode segments).
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import Base, engine, SessionLocal
from app.models import Alert
from app.core.factsheet import build_factsheet
from app.core.action_plan import generate_action_plan
from app.pipeline.composer import compose_message
from app.lang import (
    get_all_languages,
    get_verified_languages,
    get_language,
    to_target_digits,
    format_emergency_sms,
    calculate_sms_segments,
    translation_service,
)
from app.validator.engine import validate_payload
from app.voice import voice_synthesizer

client = TestClient(app)

# 7 verified target languages for acceptance
VERIFIED_TEST_LANGS = ["hi", "bn", "or", "ta", "te", "mr", "gu"]

# 3 Scenarios for acceptance testing
SCENARIOS = [
    {
        "name": "Cyclone Warning",
        "alert": {
            "identifier": "TEST-CYC-W95",
            "event": "Severe Cyclonic Storm",
            "severity": "Severe",
            "urgency": "Expected",
            "certainty": "Likely",
            "district": "Cuttack",
            "state": "Odisha",
            "headline": "Severe Cyclone Warning for Odisha coast near Cuttack.",
            "description": "Gale winds of 95 km/h gusting to 120 kmph with high swell waves of 3.8 meters expected.",
            "instruction": "Do not venture into deep sea. Inspect house roof in Cuttack.",
            "expires": datetime.now()
        },
        "persona": "general"
    },
    {
        "name": "Heavy Rain Flood",
        "alert": {
            "identifier": "TEST-FLD-R85",
            "event": "Heavy Rain Warning",
            "severity": "Extreme",
            "urgency": "Immediate",
            "certainty": "Observed",
            "district": "Wayanad",
            "state": "Kerala",
            "headline": "Flash Flood Alert for Wayanad district.",
            "description": "Extreme rainfall of 85 mm recorded. Swollen river runoff.",
            "instruction": "Evacuate low-lying inundated houses in Wayanad immediately. Do not attempt to walk in floodwaters.",
            "expires": datetime.now()
        },
        "persona": "general"
    },
    {
        "name": "Heatwave Emergency",
        "alert": {
            "identifier": "TEST-HW-T44",
            "event": "Heat Wave",
            "severity": "Extreme",
            "urgency": "Immediate",
            "certainty": "Observed",
            "district": "Nagpur",
            "state": "Maharashtra",
            "headline": "Severe Heatwave Alert for Nagpur.",
            "description": "Extreme temperature of 44 °C expected between 11 AM and 4 PM.",
            "instruction": "Avoid direct outdoor sunlight in Nagpur during extreme heat. Drink ORS frequently.",
            "expires": datetime.now()
        },
        "persona": "general"
    },
]


def setup_module():
    """Ensure test database has the scenario alerts seeded."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for sc in SCENARIOS:
        a_dict = sc["alert"]
        existing = db.query(Alert).filter(Alert.identifier == a_dict["identifier"]).first()
        if not existing:
            alert = Alert(**a_dict)
            db.add(alert)
    db.commit()
    db.close()


def test_language_registry():
    """Verify registry has full 17 target languages and filters verified ones by default."""
    all_langs = get_all_languages()
    assert len(all_langs) >= 17
    codes = {l.code for l in all_langs}
    expected_17 = {"en", "hi", "bn", "te", "mr", "ta", "ur", "gu", "kn", "or", "ml", "pa", "as", "mai", "sa", "sat", "sd"}
    assert expected_17.issubset(codes)

    verified_langs = get_verified_languages()
    verified_codes = {l.code for l in verified_langs}
    assert all(l.verified for l in verified_langs)
    # The 7 required acceptance languages must be verified
    for v in ["en", "hi", "bn", "te", "mr", "ta", "or"]:
        assert v in verified_codes

    # RTL flag check
    urdu = get_language("ur")
    assert urdu is not None and urdu.rtl is True
    hindi = get_language("hi")
    assert hindi is not None and hindi.rtl is False


def test_sms_formatting_and_segmentation():
    """Verify SMS formatting meets GSM-7 (<=160 chars) and Unicode (<= 3 segments) standards."""
    # English GSM-7
    sms_en = format_emergency_sms(grade="A", event="Cyclone", area="Cuttack", action="Evacuate kutcha houses immediately", lang="en")
    meta_en = calculate_sms_segments(sms_en)
    assert meta_en["char_count"] <= 160
    assert meta_en["segment_count"] == 1
    assert meta_en["under_three_segments"] is True

    # Hindi Unicode
    sms_hi = format_emergency_sms(grade="A", event="चक्रवात", area="कटक", action="कच्चे मकानों को तुरंत खाली करें", lang="hi")
    meta_hi = calculate_sms_segments(sms_hi)
    assert meta_hi["char_count"] <= 201
    assert meta_hi["segment_count"] <= 3
    assert meta_hi["under_three_segments"] is True


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["name"] for s in SCENARIOS])
@pytest.mark.parametrize("lang", VERIFIED_TEST_LANGS)
def test_acceptance_7_languages_3_scenarios(scenario, lang):
    """
    Acceptance Test:
    For 7 languages, generate a message for each of 3 scenarios:
    1. Validator passes (ClaimLedger status == 'PASS').
    2. Audio duration <= 30s and size < 200 KB.
    """
    a_dict = scenario["alert"]
    alert_payload = {
        "identifier": a_dict["identifier"],
        "event": a_dict["event"],
        "severity": a_dict["severity"],
        "urgency": a_dict["urgency"],
        "certainty": a_dict["certainty"],
        "district": a_dict["district"],
        "state": a_dict["state"],
        "headline": a_dict["headline"],
        "description": a_dict["description"],
        "instruction": a_dict["instruction"],
        "expires": a_dict["expires"].isoformat()
    }

    factsheet = build_factsheet(alert_payload)
    actionplan = generate_action_plan(factsheet, persona=scenario["persona"])

    fs_dict = {"facts": [f.to_dict() for f in factsheet.facts]}
    ap_dict = actionplan.to_dict()

    # Compose English base
    text_en, voice_en, ledger_en, _ = compose_message(
        alert_id=a_dict["identifier"],
        factsheet=fs_dict,
        actionplan=ap_dict
    )

    # Translate into target language
    trans_text, trans_voice, ledger, path_used = translation_service.translate_message(
        alert_id=a_dict["identifier"],
        factsheet=fs_dict,
        actionplan=ap_dict,
        text_en=text_en,
        voice_en=voice_en,
        lang=lang
    )

    # 1. Grounding validator check
    assert ledger.status == "PASS", f"Validator failed for {lang} in {scenario['name']}: {ledger.global_reason}"

    # 2. Audio duration and file size check
    synth = voice_synthesizer.synthesize(trans_voice, lang=lang)
    assert synth["audio_available"] is True
    assert synth["duration_sec"] <= 30.0, f"Duration {synth['duration_sec']}s exceeded 30s limit for {lang}"
    assert synth["file_size_bytes"] <= 200 * 1024, f"File size {synth['file_size_bytes']} exceeded 200 KB"


def test_altered_number_in_translation_is_rejected():
    """
    Acceptance Test:
    Proves that a translation that alters a number is strictly rejected by the Grounding Validator.
    """
    sc = SCENARIOS[0]  # Cyclone scenario with 95 km/h and 3.8 m
    a_dict = sc["alert"]
    alert_payload = {
        "identifier": a_dict["identifier"],
        "event": a_dict["event"],
        "severity": a_dict["severity"],
        "urgency": a_dict["urgency"],
        "certainty": a_dict["certainty"],
        "district": a_dict["district"],
        "state": a_dict["state"],
        "headline": a_dict["headline"],
        "description": a_dict["description"],
        "instruction": a_dict["instruction"],
        "expires": a_dict["expires"].isoformat()
    }

    factsheet = build_factsheet(alert_payload)
    actionplan = generate_action_plan(factsheet, persona="general")

    fs_dict = {"facts": [f.to_dict() for f in factsheet.facts]}
    ap_dict = actionplan.to_dict()

    # Valid Hindi translation has '९५' (95)
    valid_payload = {
        "text_script_sentences": [{
            "text": "कटक में ९५ किमी/घंटा हवाओं से पहले आपातकालीन किट तैयार करें।",
            "fact_ids": ["F7"],
            "action_ids": ["ACT-CYC-B-GEN-02"]
        }],
        "voice_script_sentences": [{
            "text": "कटक में ९५ किमी/घंटा हवाओं से पहले आपातकालीन किट तैयार करें।",
            "fact_ids": ["F7"],
            "action_ids": ["ACT-CYC-B-GEN-02"]
        }]
    }
    valid_ledger = validate_payload(valid_payload, a_dict["identifier"], fs_dict, ap_dict, lang="hi")
    assert valid_ledger.status == "PASS"

    # TAMPERED: Altered number from 95 to 150 (१५० in Devanagari)
    tampered_payload_devanagari = {
        "text_script_sentences": [{
            "text": "कटक में १५० किमी/घंटा हवाओं से पहले आपातकालीन किट तैयार करें।",  # 150 instead of 95!
            "fact_ids": ["F7"],
            "action_ids": ["ACT-CYC-B-GEN-02"]
        }],
        "voice_script_sentences": [{
            "text": "कटक में १५० किमी/घंटा हवाओं से पहले आपातकालीन किट तैयार करें।",
            "fact_ids": ["F7"],
            "action_ids": ["ACT-CYC-B-GEN-02"]
        }]
    }
    rejected_ledger1 = validate_payload(tampered_payload_devanagari, a_dict["identifier"], fs_dict, ap_dict, lang="hi")
    assert rejected_ledger1.status == "FAIL", "Validator failed to block altered number in Devanagari translation!"

    # TAMPERED: Altered number in Odia (୧୫୦ = 150 instead of ୯୫ = 95)
    tampered_payload_odia = {
        "text_script_sentences": [{
            "text": "କଟକ ରେ ୧୫୦ କିମି/ଘଣ୍ଟା ପବନ ପୂର୍ବରୁ କିଟ୍ ପ୍ରସ୍ତୁତ ରଖନ୍ତୁ।",  # 150 instead of 95!
            "fact_ids": ["F7"],
            "action_ids": ["ACT-CYC-B-GEN-02"]
        }],
        "voice_script_sentences": [{
            "text": "କଟକ ରେ ୧୫୦ କିମି/ଘଣ୍ଟା ପବନ ପୂର୍ବରୁ କିଟ୍ ପ୍ରସ୍ତୁତ ରଖନ୍ତୁ।",
            "fact_ids": ["F7"],
            "action_ids": ["ACT-CYC-B-GEN-02"]
        }]
    }
    rejected_ledger2 = validate_payload(tampered_payload_odia, a_dict["identifier"], fs_dict, ap_dict, lang="or")
    assert rejected_ledger2.status == "FAIL", "Validator failed to block altered number in Odia translation!"


def test_voice_api_endpoint():
    """Verify POST /api/voice produces audio_url, transcript, and claim_ledger."""
    resp = client.post("/api/voice", json={
        "alert_id": "TEST-CYC-W95",
        "persona": "general",
        "lang": "hi"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["alert_id"] == "TEST-CYC-W95"
    assert data["lang"] == "hi"
    assert data["transcript"] is not None and len(data["transcript"]) > 0
    assert data["sms_text"] is not None
    assert data["claim_ledger"]["status"] == "PASS"
    assert data["audio_available"] is True
    assert data["duration_sec"] <= 30.0
    assert data["audio_url"] is not None

    # Verify audio download endpoint
    audio_resp = client.get(data["audio_url"])
    assert audio_resp.status_code == 200
    assert len(audio_resp.content) > 0
    assert len(audio_resp.content) <= 200 * 1024


def test_languages_api_endpoint():
    """Verify GET /api/languages filters verified languages by default and returns 17 with ?all=true."""
    # Default (verified only)
    resp_def = client.get("/api/languages")
    assert resp_def.status_code == 200
    langs_def = resp_def.json()["languages"]
    assert all(l["verified"] for l in langs_def)
    assert len(langs_def) >= 7

    # All languages
    resp_all = client.get("/api/languages?all=true")
    assert resp_all.status_code == 200
    langs_all = resp_all.json()["languages"]
    assert len(langs_all) >= 17
