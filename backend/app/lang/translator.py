"""
Translation Service for SkySafe AI.
Provider chain: Sarvam API (if key) -> Deterministic Template Pack -> English fallback.
All translations are strictly grounded and validated through the Grounding Validator.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple, Optional, List

from app.lang.templates.pack import get_localized_action, ACTION_TEMPLATES
from app.lang.digits import render_fact_slot, to_target_digits
from app.validator.engine import validate_payload
from app.validator.models import ClaimLedger

logger = logging.getLogger("app")


class TranslationService:
    def __init__(self):
        self.sarvam_api_key = os.getenv("SARVAM_API_KEY")
        self.timeout = 6.0

    def _call_sarvam_translate(self, text: str, target_lang: str) -> Optional[str]:
        """Call Sarvam AI translation API."""
        if not self.sarvam_api_key:
            return None
            
        url = "https://api.sarvam.ai/translate"
        # Sarvam language code mapping (e.g. hi-IN, bn-IN, te-IN, mr-IN, ta-IN, od-IN, gu-IN)
        sarvam_code = f"{target_lang}-IN" if "-" not in target_lang else target_lang
        if target_lang == "or":
            sarvam_code = "od-IN"

        payload = {
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": sarvam_code,
            "speaker_gender": "Female",
            "mode": "formal"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "api-subscription-key": self.sarvam_api_key
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("translated_text")
        except Exception as e:
            logger.warning(f"Sarvam translation failed for {target_lang}: {e}")
            return None

    def _build_template_pack_payload(
        self,
        factsheet: Dict[str, Any],
        actionplan: Dict[str, Any],
        lang: str
    ) -> Dict[str, Any]:
        """
        Build a deterministic localized payload using per-language template packs
        and native digits rendering.
        """
        # Extract fact slot values from factsheet
        facts_map = {}
        for f in factsheet.get("facts", []):
            field = f.get("field")
            val = f.get("value")
            if field:
                facts_map[field] = val

        ordered_actions = actionplan.get("ordered_actions", [])
        text_sentences = []
        voice_sentences = []
        total_text_words = 0
        total_voice_words = 0

        for idx, action in enumerate(ordered_actions):
            aid = action.get("id")
            fact_refs = action.get("fact_refs", [])
            loc_text = get_localized_action(aid, facts_map, lang=lang)
            if not loc_text:
                # Fallback to action's original text
                loc_text = action.get("action", "")

            sentence_facts = list(fact_refs)
            for f in factsheet.get("facts", []):
                fid = f.get("id")
                fval = str(f.get("value"))
                if fid not in sentence_facts and (fval in loc_text or to_target_digits(fval, lang) in loc_text):
                    sentence_facts.append(fid)

            sent_obj = {
                "text": loc_text,
                "fact_ids": sentence_facts,
                "action_ids": [aid] if aid else []
            }

            words_count = len(loc_text.split())
            if total_text_words + words_count <= 60 or not text_sentences:
                text_sentences.append(sent_obj)
                total_text_words += words_count

            if total_voice_words + words_count <= 45 or not voice_sentences:
                voice_sentences.append(sent_obj)
                total_voice_words += words_count

        return {
            "text_script_sentences": text_sentences,
            "voice_script_sentences": voice_sentences
        }

    def translate_message(
        self,
        alert_id: str,
        factsheet: Dict[str, Any],
        actionplan: Dict[str, Any],
        text_en: str,
        voice_en: str,
        lang: str = "en"
    ) -> Tuple[str, str, ClaimLedger, str]:
        """
        Translates message following provider hierarchy:
        Sarvam -> Deterministic Template Pack -> English fallback.
        Strictly passes all output through GroundingValidator.
        Returns: (text_script, voice_script, claim_ledger, path_used)
        """
        lang = lang.lower()
        if lang == "en":
            payload = {
                "text_script_sentences": [{"text": text_en, "fact_ids": [f["id"] for f in factsheet.get("facts", [])], "action_ids": [a["id"] for a in actionplan.get("ordered_actions", [])]}],
                "voice_script_sentences": [{"text": voice_en, "fact_ids": [f["id"] for f in factsheet.get("facts", [])], "action_ids": [a["id"] for a in actionplan.get("ordered_actions", [])]}],
            }
            ledger = validate_payload(payload, alert_id, factsheet, actionplan, lang="en")
            return text_en, voice_en, ledger, "english"

        # 1. Try Sarvam Translate if API key is present
        if self.sarvam_api_key:
            trans_text = self._call_sarvam_translate(text_en, lang)
            trans_voice = self._call_sarvam_translate(voice_en, lang)
            if trans_text and trans_voice:
                sarvam_payload = {
                    "text_script_sentences": [{
                        "text": trans_text,
                        "fact_ids": [f["id"] for f in factsheet.get("facts", [])],
                        "action_ids": [a["id"] for a in actionplan.get("ordered_actions", [])]
                    }],
                    "voice_script_sentences": [{
                        "text": trans_voice,
                        "fact_ids": [f["id"] for f in factsheet.get("facts", [])],
                        "action_ids": [a["id"] for a in actionplan.get("ordered_actions", [])]
                    }]
                }
                ledger = validate_payload(sarvam_payload, alert_id, factsheet, actionplan, lang=lang)
                if ledger.status == "PASS":
                    logger.info(f"Sarvam translation passed validation for {lang}")
                    return trans_text, trans_voice, ledger, "sarvam_translate"
                else:
                    logger.warning(f"Sarvam translation for {lang} failed validation: {ledger.global_reason}. Falling back to template pack.")

        # 2. Deterministic Template Pack
        template_payload = self._build_template_pack_payload(factsheet, actionplan, lang=lang)
        ledger = validate_payload(template_payload, alert_id, factsheet, actionplan, lang=lang)
        if ledger.status == "PASS":
            text = " ".join(s["text"] for s in template_payload["text_script_sentences"])
            voice = " ".join(s["text"] for s in template_payload["voice_script_sentences"])
            return text, voice, ledger, "template_pack"
        else:
            logger.warning(f"Template pack for {lang} failed validation: {ledger.global_reason}. Falling back to English.")

        # 3. English Fallback
        english_payload = {
            "text_script_sentences": [{"text": text_en, "fact_ids": [f["id"] for f in factsheet.get("facts", [])], "action_ids": [a["id"] for a in actionplan.get("ordered_actions", [])]}],
            "voice_script_sentences": [{"text": voice_en, "fact_ids": [f["id"] for f in factsheet.get("facts", [])], "action_ids": [a["id"] for a in actionplan.get("ordered_actions", [])]}],
        }
        ledger = validate_payload(english_payload, alert_id, factsheet, actionplan, lang="en")
        return text_en, voice_en, ledger, "english_fallback"


translation_service = TranslationService()
