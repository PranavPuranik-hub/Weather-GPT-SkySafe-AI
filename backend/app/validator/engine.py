"""
Deterministic Grounding Engine for validating LLM outputs.
"""
import re
from typing import Any, Dict, List

from app.validator.extractor import extract_numeric_tokens, extract_time_tokens
from app.validator.models import ClaimLedger, FactCheck, SentenceValidation
from app.validator.normalizer import normalize_text_for_numbers


def extract_all_numeric_info(text: str) -> List[str]:
    norm = normalize_text_for_numbers(text)
    nums = extract_numeric_tokens(norm)
    times = extract_time_tokens(norm)
    return list(set(nums + times))

def convert_units(val: float, from_unit: str, to_unit: str) -> float:
    # Basic unit conversions
    if from_unit == 'kmh' and to_unit == 'knots':
        return val * 0.539957
    if from_unit == 'knots' and to_unit == 'kmh':
        return val * 1.852
    return val

def fuzzy_match_number(token: str, fact_value: str) -> bool:
    """Check if token matches fact_value, accounting for rounding/units."""
    token = token.lower()
    fact_value = str(fact_value).lower()

    # Direct match
    if token == fact_value or token in fact_value or fact_value in token:
        return True

    # Numeric match
    token_match = re.search(r'(\d+(?:\.\d+)?)', token)
    fact_match = re.search(r'(\d+(?:\.\d+)?)', fact_value)

    if token_match and fact_match:
        t_val = float(token_match.group(1))
        f_val = float(fact_match.group(1))

        if abs(t_val - f_val) < 0.1:
            return True

        # Try unit conversions if units are present
        if 'kmh' in fact_value and 'knot' in token:
            if abs(convert_units(f_val, 'kmh', 'knots') - t_val) < 1.0:
                return True
        if 'knot' in fact_value and 'kmh' in token:
            if abs(convert_units(f_val, 'knots', 'kmh') - t_val) < 1.0:
                return True

    return False

def check_negations(text: str, action_text: str, lang: str = "en") -> bool:
    """
    Ensure critical negations in the action are preserved in the text.
    Supports English and major Indic languages.
    """
    negations = ["not", "no", "never", "don't", "do not", "avoid"]
    action_lower = action_text.lower()
    text_lower = text.lower()

    action_has_negation = any(re.search(rf'\b{neg}\b', action_lower) for neg in negations)
    if not action_has_negation:
        return True

    if lang == "en":
        for neg in negations:
            if re.search(rf'\b{neg}\b', text_lower):
                return True
        return False
    else:
        multilingual_negations = {
            "hi": ["मत", "न", "नहीं", "बचें", "रोकें"],
            "bn": ["না", "করবেন না", "যাবেন না", "এড়িয়ে", "বন্ধ"],
            "or": ["ନାହିଁ", "କରନ୍ତୁ ନାହିଁ", "ଯାଆନ୍ତୁ ନାହିଁ", "ଦୂରେଇ", "ବନ୍ଦ"],
            "ta": ["வேண்டாம்", "கூடாது", "தவிர்க்கவும்", "நிறுத்தவும்"],
            "te": ["వద్దు", "చేయవద్దు", "వెళ్లవద్దు", "నివారించండి", "ఆపండి"],
            "mr": ["नका", "नाही", "टाळा", "बंद"],
            "gu": ["ન", "નહીં", "નથી", "ટાળો", "બંધ"],
        }
        lang_negs = multilingual_negations.get(lang.lower(), [])
        if any(neg in text for neg in lang_negs) or any(re.search(rf'\b{neg}\b', text_lower) for neg in negations):
            return True
        return False

def validate_sentence(
    sentence_idx: int,
    text: str,
    declared_fact_ids: List[str],
    declared_action_ids: List[str],
    factsheet: Dict[str, Any],
    actionplan: Dict[str, Any],
    lang: str = "en"
) -> SentenceValidation:

    token_checks = []
    status = "PASS"
    reason = None

    # 1. Extract numbers and times (normalizes Indic numerals across all scripts)
    tokens = extract_all_numeric_info(text)

    # Resolve facts
    facts_map = {f['id']: f['value'] for f in factsheet.get('facts', [])}
    allowed_fact_values = [facts_map[fid] for fid in declared_fact_ids if fid in facts_map]
    all_fact_values = list(facts_map.values())

    # Resolve actions
    ap_map = {a['id']: a.get('action', a.get('instruction', '')) for a in actionplan.get('ordered_actions', [])}

    for token in tokens:
        # Does the token match any declared fact?
        matched_fid = None
        for fid in declared_fact_ids:
            if fid in facts_map and fuzzy_match_number(token, facts_map[fid]):
                matched_fid = fid
                break

        if matched_fid:
            token_checks.append(FactCheck(token=token, fact_id=matched_fid, status="PASS"))
        elif any(fuzzy_match_number(token, ap_map.get(aid, '')) for aid in declared_action_ids):
            # The token is part of an approved curated ActionLibrary instruction
            token_checks.append(FactCheck(token=token, status="PASS"))
        else:
            # Let's see if it matches an UNDECLARED fact
            matched_undeclared = None
            for fid, fval in facts_map.items():
                if fuzzy_match_number(token, fval):
                    matched_undeclared = fid
                    break

            if matched_undeclared:
                token_checks.append(FactCheck(
                    token=token,
                    fact_id=matched_undeclared,
                    status="FAIL",
                    reason=f"Matches fact {matched_undeclared} but it was not declared in fact_ids"
                ))
                status = "FAIL"
                reason = "Undeclared fact usage"
            else:
                token_checks.append(FactCheck(
                    token=token,
                    status="FAIL",
                    reason="Hallucinated numeric token/time not found in any facts"
                ))
                status = "FAIL"
                reason = "Hallucination detected"

    # 2. Check Actions
    if declared_action_ids:
        for aid in declared_action_ids:
            if aid not in ap_map:
                status = "FAIL"
                reason = f"Invented action_id {aid}"
                break
            else:
                action_text = ap_map[aid]
                # Check negations
                if not check_negations(text, action_text, lang=lang):
                    status = "FAIL"
                    reason = f"Dropped critical negation for action {aid}"
                    break

                # Check keyword overlap
                if lang == "en":
                    action_words = set(re.findall(r'\b\w{4,}\b', action_text.lower()))
                    text_words = set(re.findall(r'\b\w{4,}\b', text.lower()))
                    if action_words and not action_words.intersection(text_words):
                        status = "FAIL"
                        reason = f"Action {aid} was declared but text lacks any keywords from it."
                        break
                else:
                    # In multilingual mode, check localized keywords if available
                    from app.lang.templates.pack import ACTION_TEMPLATES
                    loc_tmpl = ACTION_TEMPLATES.get(aid, {}).get(lang)
                    if loc_tmpl:
                        loc_words = set(re.findall(r'[\w]{3,}', loc_tmpl))
                        text_words = set(re.findall(r'[\w]{3,}', text))
                        if loc_words and not loc_words.intersection(text_words):
                            status = "FAIL"
                            reason = f"Action {aid} translation lacks keywords from target template."
                            break

    # Ensure sentence declares something
    if not declared_fact_ids and not declared_action_ids:
        status = "FAIL"
        reason = "Sentence declares no facts or actions (invented content)."

    # 3. Check for fake locations/helplines
    for token in tokens:
        digits = re.sub(r'\D', '', token)
        if len(digits) >= 10:
            if not any(digits in str(fval) for fval in all_fact_values):
                status = "FAIL"
                reason = "Hallucinated helpline/phone number"

    # Place names - Extract proper nouns / check against fake places
    fake_places = [
        "Mumbai", "Delhi", "Unknown", "Atlantis", "Chennai", "Kolkata", "Bengaluru", "London", "Paris", "Washington", "FakeCity", "New York",
        "मुंबई", "दिल्ली", "कोलकाता", "चेन्नई", "அட்லாண்டிஸ்", "ముంబై", "মুম্বই"
    ]
    for fp in fake_places:
        if re.search(rf'\b{re.escape(fp)}\b', text, re.IGNORECASE) and not any(fp.lower() in str(fval).lower() for fval in all_fact_values):
            status = "FAIL"
            reason = f"Hallucinated place name '{fp}'"
            break

    # Geographic Coherence Check: ensure known districts are not falsely paired with an incorrect state
    KNOWN_DISTRICT_TO_STATE = {
        "nagpur": "Maharashtra",
        "mumbai": "Maharashtra",
        "ratnagiri": "Maharashtra",
        "pune": "Maharashtra",
        "cuttack": "Odisha",
        "puri": "Odisha",
        "bhubaneswar": "Odisha",
        "khordha": "Odisha",
        "ganjam": "Odisha",
        "balasore": "Odisha",
        "wayanad": "Kerala",
        "kozhikode": "Kerala",
        "ernakulam": "Kerala",
        "idukki": "Kerala",
        "churu": "Rajasthan",
        "bikaner": "Rajasthan",
        "jaipur": "Rajasthan",
        "patna": "Bihar",
        "chennai": "Tamil Nadu",
        "cuddalore": "Tamil Nadu",
        "visakhapatnam": "Andhra Pradesh",
        "uttarkashi": "Uttarakhand",
    }
    INDIAN_STATES = [
        "Odisha", "Maharashtra", "Kerala", "Rajasthan", "Bihar",
        "Tamil Nadu", "Andhra Pradesh", "Uttarakhand", "West Bengal", "Gujarat"
    ]

    for dist, expected_state in KNOWN_DISTRICT_TO_STATE.items():
        if re.search(rf'\b{re.escape(dist)}\b', text, re.IGNORECASE):
            for conflict_state in INDIAN_STATES:
                if conflict_state.lower() != expected_state.lower():
                    # Check for pattern "District, State" or "District in State"
                    pair_pattern = rf'\b{re.escape(dist)}\b[\s,]+(?:in\s+)?{re.escape(conflict_state)}\b'
                    rev_pattern = rf'\b{re.escape(conflict_state)}\b[\s,]+(?:in\s+)?{re.escape(dist)}\b'
                    if re.search(pair_pattern, text, re.IGNORECASE) or re.search(rev_pattern, text, re.IGNORECASE):
                        status = "FAIL"
                        reason = f"Geographic discrepancy: '{dist.title()}' is in '{expected_state}', not '{conflict_state}'."
                        break
            if status == "FAIL":
                break

    return SentenceValidation(
        sentence_index=sentence_idx,
        text=text,
        declared_fact_ids=declared_fact_ids,
        declared_action_ids=declared_action_ids,
        token_checks=token_checks,
        status=status,
        reason=reason
    )

def validate_payload(
    payload: Dict[str, Any],
    alert_id: str,
    factsheet: Dict[str, Any],
    actionplan: Dict[str, Any],
    lang: str = "en"
) -> ClaimLedger:

    text_sentences = payload.get("text_script_sentences", [])
    voice_sentences = payload.get("voice_script_sentences", [])

    text_vals = []
    for i, s in enumerate(text_sentences):
        text_vals.append(validate_sentence(
            i,
            s.get("text", ""),
            s.get("fact_ids", []),
            s.get("action_ids", []),
            factsheet,
            actionplan,
            lang=lang
        ))

    voice_vals = []
    for i, s in enumerate(voice_sentences):
        voice_vals.append(validate_sentence(
            i,
            s.get("text", ""),
            s.get("fact_ids", []),
            s.get("action_ids", []),
            factsheet,
            actionplan,
            lang=lang
        ))

    global_status = "PASS"
    global_reason = None

    if any(v.status == "FAIL" for v in text_vals + voice_vals):
        global_status = "FAIL"

    # Check word count constraints
    text_words = sum(len(s.get("text", "").split()) for s in text_sentences)
    voice_words = sum(len(s.get("text", "").split()) for s in voice_sentences)

    if text_words > 60:
        global_status = "FAIL"
        global_reason = f"Text script exceeds 60 words ({text_words})"
    if voice_words > 45:
        global_status = "FAIL"
        global_reason = f"Voice script exceeds 45 words ({voice_words})"

    return ClaimLedger(
        alert_id=alert_id,
        status=global_status,
        text_validations=text_vals,
        voice_validations=voice_vals,
        global_reason=global_reason
    )
