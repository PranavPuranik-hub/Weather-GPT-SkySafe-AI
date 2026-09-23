"""
Voice and Audio Notes API Router.
Endpoints for synthesizing voice notes, serving audio files, and checking languages.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.action_plan import generate_action_plan
from app.core.db import SessionLocal
from app.core.factsheet import build_factsheet
from app.lang.registry import get_all_languages, get_verified_languages
from app.lang.sms import calculate_sms_segments, format_emergency_sms
from app.lang.translator import translation_service
from app.models import Alert
from app.pipeline.composer import compose_message
from app.voice.models import VoiceRequest, VoiceResponse
from app.voice.synthesizer import AUDIO_CACHE_DIR, voice_synthesizer

voice_router = APIRouter(prefix="/api/voice", tags=["voice"])
languages_router = APIRouter(prefix="/api/languages", tags=["languages"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@voice_router.post("", response_model=VoiceResponse)
def create_voice_note(req: VoiceRequest, db: Session = Depends(get_db)):
    """
    Generate voice note for an alert in the requested persona and language.
    Executes grounding validation, per-language translation, and TTS synthesis.
    """
    alert = db.query(Alert).filter(Alert.identifier == req.alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{req.alert_id}' not found")

    alert_dict = {
        "identifier": alert.identifier,
        "event": alert.event,
        "severity": alert.severity,
        "urgency": alert.urgency,
        "certainty": alert.certainty,
        "district": alert.district,
        "state": alert.state,
        "headline": alert.headline,
        "description": alert.description,
        "instruction": alert.instruction,
        "expires": alert.expires.isoformat() if alert.expires else None
    }

    # 1. Build FactSheet & ActionPlan
    factsheet = build_factsheet(alert_dict)
    actionplan = generate_action_plan(factsheet, persona=req.persona)

    fs_dict = {"facts": [f.to_dict() for f in factsheet.facts]}
    ap_dict = actionplan.to_dict()

    # 2. Compose Base Message
    text_en, voice_en, ledger_en, path_en = compose_message(
        alert_id=req.alert_id,
        factsheet=fs_dict,
        actionplan=ap_dict
    )

    # 3. Translate if target lang != "en"
    if req.lang.lower() != "en":
        text, voice_script, ledger, path_used = translation_service.translate_message(
            alert_id=req.alert_id,
            factsheet=fs_dict,
            actionplan=ap_dict,
            text_en=text_en,
            voice_en=voice_en,
            lang=req.lang
        )
    else:
        text = text_en
        voice_script = voice_en
        ledger = ledger_en
        path_used = path_en

    # 4. Generate Voice Note
    synth_result = voice_synthesizer.synthesize(voice_script, lang=req.lang)

    # 5. Build SMS emergency version
    if actionplan.ordered_actions:
        first_act = actionplan.ordered_actions[0]
        primary_action = first_act.get("action", "") if isinstance(first_act, dict) else getattr(first_act, "action", "Stay alert")
    else:
        primary_action = "Stay alert"

    sms_text = format_emergency_sms(
        grade=actionplan.grade,
        event=alert.event,
        area=alert.district or alert.state or "Area",
        action=primary_action,
        lang=req.lang
    )
    sms_meta = calculate_sms_segments(sms_text)

    return VoiceResponse(
        alert_id=req.alert_id,
        persona=req.persona,
        lang=req.lang,
        audio_url=synth_result["audio_url"],
        transcript=voice_script,
        sms_text=sms_text,
        sms_metadata=sms_meta,
        claim_ledger=ledger.dict() if hasattr(ledger, "dict") else ledger.model_dump(),
        duration_sec=synth_result["duration_sec"],
        file_size_bytes=synth_result["file_size_bytes"],
        audio_available=synth_result["audio_available"],
        browser_speech=synth_result["browser_speech"],
        browser_script=voice_script,
        path_used=path_used
    )


@voice_router.get("/audio/{filename}")
def serve_audio(filename: str):
    """Serve cached synthesized audio files."""
    file_path = AUDIO_CACHE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    return FileResponse(file_path, media_type=media_type)


@languages_router.get("")
def list_languages(all_langs: bool = Query(default=False, alias="all")):
    """
    List supported languages.
    By default, returns only verified languages for UI display.
    Pass ?all=true to retrieve all configured languages.
    """
    if all_langs:
        langs = get_all_languages()
    else:
        langs = get_verified_languages()
    return {"languages": [l.dict() if hasattr(l, "dict") else l.model_dump() for l in langs]}
