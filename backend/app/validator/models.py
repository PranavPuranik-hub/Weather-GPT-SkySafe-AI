"""
Models for the Grounding Validator.
"""
from typing import List, Optional

from pydantic import BaseModel


class FactCheck(BaseModel):
    token: str
    fact_id: Optional[str] = None
    status: str  # "PASS", "FAIL"
    reason: Optional[str] = None

class SentenceValidation(BaseModel):
    sentence_index: int
    text: str
    declared_fact_ids: List[str]
    declared_action_ids: List[str]
    token_checks: List[FactCheck]
    status: str # "PASS", "FAIL"
    reason: Optional[str] = None

class ClaimLedger(BaseModel):
    alert_id: str
    status: str # "PASS", "FAIL"
    text_validations: List[SentenceValidation]
    voice_validations: List[SentenceValidation]
    global_reason: Optional[str] = None

    def get_violations_text(self) -> str:
        violations = []
        for v in self.text_validations + self.voice_validations:
            if v.status == "FAIL":
                violations.append(f"Sentence: '{v.text}' - Reason: {v.reason}")
                for check in v.token_checks:
                    if check.status == "FAIL":
                        violations.append(f"  Token '{check.token}': {check.reason}")
        if self.global_reason:
            violations.append(f"Global: {self.global_reason}")
        return "\n".join(violations)
