"""
Adversarial evaluation: exposes run_adversarial_check for the Break-it Panel.
Reuses the single MisbehavingLLMClient definition from app.llm.misbehaving_client.
Reuses validate_payload from the grounding validator.
"""
import json
import logging
from typing import Any, Dict, Tuple

from app.llm.misbehaving_client import MisbehavingLLMClient
from app.llm.template_client import TemplateClient
from app.llm.prompts import REWORDING_SYSTEM_PROMPT, RESPONSE_JSON_SCHEMA, build_user_prompt
from app.validator.engine import validate_payload
from app.core.factsheet import FactSheet, Fact, build_factsheet
from app.core.action_plan import generate_action_plan

logger = logging.getLogger("app.eval.adversarial")

# Shared adversarial FactSheet matching test_adversarial.py
ADVERSARIAL_FACTSHEET = {
    "facts": [
        {"id": "F1", "field": "event", "value": "Cyclone"},
        {"id": "F2", "field": "wind_speed", "value": "120 kmh"},
        {"id": "F3", "field": "time", "value": "14:30"},
        {"id": "F4", "field": "location", "value": "Cuttack"},
    ]
}
ADVERSARIAL_ACTIONPLAN = {
    "ordered_actions": [
        {"id": "a1", "instruction": "Do not go out to sea."},
        {"id": "a2", "instruction": "Evacuate immediately."},
        {"id": "a3", "instruction": "Keep emergency kit ready."},
    ]
}


def run_adversarial_check(
    text: str,
    use_misbehaving_llm: bool = False,
    factsheet: Dict[str, Any] = None,
    actionplan: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Run a judge-supplied text through the compose → validate pipeline.

    When use_misbehaving_llm=True, the MisbehavingLLMClient (single definition)
    replaces the normal client. The validator MUST still catch the hallucination.
    The unsafe response is NEVER returned — only the fallback is.

    Returns: {response, claim_ledger, validator_result, fallback_triggered, path_used}
    """
    fs = factsheet or ADVERSARIAL_FACTSHEET
    ap = actionplan or ADVERSARIAL_ACTIONPLAN

    alert_id = "BREAKIT-EVAL"

    if use_misbehaving_llm:
        client = MisbehavingLLMClient()
        path_name = "misbehaving_llm"
    else:
        client = TemplateClient()
        path_name = "template"

    # Build prompt with the judge's text injected as context
    user_prompt = build_user_prompt(json.dumps(fs), json.dumps(ap))
    # Append the judge's message as an adversarial signal
    user_prompt += f"\n\nJUDGE INPUT: {text}"

    try:
        raw = client.generate(REWORDING_SYSTEM_PROMPT, user_prompt, RESPONSE_JSON_SCHEMA)
        payload = json.loads(raw)
    except Exception as e:
        logger.warning(f"Client generation error: {e}")
        payload = {"text_script_sentences": [{"text": text, "fact_ids": [], "action_ids": []}],
                   "voice_script_sentences": []}

    ledger = validate_payload(payload, alert_id, fs, ap)
    fallback_triggered = ledger.status == "FAIL"

    # If validation failed, always substitute safe deterministic fallback
    if fallback_triggered:
        tc = TemplateClient()
        safe_raw = tc.generate(REWORDING_SYSTEM_PROMPT, build_user_prompt(json.dumps(fs), json.dumps(ap)), RESPONSE_JSON_SCHEMA)
        safe_payload = json.loads(safe_raw)
        safe_ledger = validate_payload(safe_payload, alert_id, fs, ap)
        response_text = " ".join(
            s.get("text", "") for s in safe_payload.get("text_script_sentences", [])
        )
        path_name = "template_fallback"
    else:
        response_text = " ".join(
            s.get("text", "") for s in payload.get("text_script_sentences", [])
        )
        safe_ledger = ledger

    ledger_dict = ledger.model_dump() if hasattr(ledger, "model_dump") else ledger.dict()
    safe_ledger_dict = safe_ledger.model_dump() if hasattr(safe_ledger, "model_dump") else safe_ledger.dict()

    return {
        "response": response_text,
        "original_validator_result": ledger_dict,
        "final_validator_result": safe_ledger_dict,
        "fallback_triggered": fallback_triggered,
        "path_used": path_name,
        "misbehaving_llm_used": use_misbehaving_llm,
        "blocked": fallback_triggered,
    }
