"""
MisbehavingLLMClient: A deliberately broken LLM client for adversarial testing.

This is the single, authoritative definition of adversarial LLM behavior in the codebase.
It is used by both the adversarial test suite (tests/validator/test_adversarial.py) and the
Break-it Panel (app/eval/adversarial.py) via import.

NEVER use this client in any production code path.
"""
import json
from typing import Any, Dict

from app.llm.client import LLMClient


class MisbehavingLLMClient(LLMClient):
    """
    A deliberately misbehaving LLM client that produces ungrounded numbers.
    Used to verify the grounding validator catches and blocks invalid output.
    Never bypass validation — all outputs from this client must pass through validate_payload.
    """

    def __init__(self, ungrounded_number: str = "200 kmh", fake_place: str = "Atlantis") -> None:
        self.ungrounded_number = ungrounded_number
        self.fake_place = fake_place

    def generate(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any]) -> str:
        """Produces a response with a hallucinated wind speed and fabricated place name."""
        hallucinated_text = (
            f"WARNING: Wind speed will reach {self.ungrounded_number} in {self.fake_place}. "
            f"Evacuate {self.fake_place} now!"
        )
        result = {
            "text_script_sentences": [
                {
                    "text": hallucinated_text,
                    "fact_ids": [],
                    "action_ids": []
                }
            ],
            "voice_script_sentences": [
                {
                    "text": hallucinated_text,
                    "fact_ids": [],
                    "action_ids": []
                }
            ]
        }
        return json.dumps(result)
