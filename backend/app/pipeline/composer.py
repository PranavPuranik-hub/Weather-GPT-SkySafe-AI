"""
Pipeline Coordinator for Generation and Validation.
"""
import json
import logging
from typing import Any, Dict, Tuple

from app.llm.prompts import RESPONSE_JSON_SCHEMA, REWORDING_SYSTEM_PROMPT, build_user_prompt
from app.llm.provider import TemplateClient, generate_with_fallback
from app.validator.engine import validate_payload
from app.validator.models import ClaimLedger

logger = logging.getLogger("app")

def compose_message(
    alert_id: str,
    factsheet: Dict[str, Any],
    actionplan: Dict[str, Any]
) -> Tuple[str, str, ClaimLedger, str]:
    """
    generate -> validate -> retry (max 2) -> fallback
    Returns: (text_script, voice_script, claim_ledger, path_used)
    """

    fs_json = json.dumps(factsheet)
    ap_json = json.dumps(actionplan)

    violations = ""
    max_retries = 2
    path_used = "llm_ok"
    final_payload = None
    final_ledger = None

    for attempt in range(max_retries + 1):
        user_prompt = build_user_prompt(fs_json, ap_json, violations)

        try:
            response_text, provider_path = generate_with_fallback(
                REWORDING_SYSTEM_PROMPT,
                user_prompt,
                RESPONSE_JSON_SCHEMA
            )

            payload = json.loads(response_text)
            ledger = validate_payload(payload, alert_id, factsheet, actionplan)

            if ledger.status == "PASS":
                final_payload = payload
                final_ledger = ledger
                # If we retried at least once and succeeded, mark as llm_retry
                if attempt > 0:
                    path_used = "llm_retry"
                # If provider itself fell back to template initially, we use that.
                if provider_path == "template":
                    path_used = "template_fallback"
                break
            else:
                logger.warning(f"Validation failed on attempt {attempt+1}. Reason: {ledger.global_reason}")
                violations = ledger.get_violations_text()

        except Exception as e:
            logger.error(f"Generation error on attempt {attempt+1}: {e}")
            violations = f"System Error: {str(e)}"

    # If all attempts fail, use deterministic fallback directly
    if not final_payload:
        logger.warning("All LLM attempts failed or were rejected. Falling back to template.")
        tc = TemplateClient()
        fallback_text = tc.generate(REWORDING_SYSTEM_PROMPT, build_user_prompt(fs_json, ap_json), RESPONSE_JSON_SCHEMA)
        final_payload = json.loads(fallback_text)
        final_ledger = validate_payload(final_payload, alert_id, factsheet, actionplan)
        path_used = "template_fallback"

    text_script = " ".join([s.get("text", "") for s in final_payload.get("text_script_sentences", [])])
    voice_script = " ".join([s.get("text", "") for s in final_payload.get("voice_script_sentences", [])])

    return text_script, voice_script, final_ledger, path_used
