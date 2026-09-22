"""
Template fallback client implementation.
"""
import json
import logging
from typing import Any, Dict

from app.llm.client import LLMClient

logger = logging.getLogger("app")

class TemplateClient(LLMClient):
    def generate(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any]) -> str:
        logger.info("TemplateClient generating fallback text")
        
        # We try to extract ActionPlan from user_prompt string or just fallback completely.
        # Since this is deterministic, we'll return a safe generic string based on standard actions,
        # but realistically the composer should construct this or we just output a very safe JSON.
        
        # We will parse out action_ids from the user_prompt if we can, 
        # or just return a default valid json.
        
        actions_text = "Please follow safety instructions immediately."
        action_ids = []
        action_texts = []
        fact_ids = []
        
        try:
            if "FactSheet:" in user_prompt:
                # very naive way to find facts in factsheet block
                # but we can just regex for F[0-9]+
                import re
                fact_ids = list(set(re.findall(r'"id":\s*"(F\d+)"', user_prompt)))
            if "ActionPlan:" in user_prompt:
                ap_str = user_prompt.split("ActionPlan:")[1].strip()
                if "PREVIOUS ATTEMPT" in ap_str:
                    ap_str = ap_str.split("PREVIOUS ATTEMPT")[0].strip()
                ap_data = json.loads(ap_str)
                for a in ap_data.get("ordered_actions", []):
                    action_ids.append(a.get("id"))
                    action_texts.append(a.get("instruction", a.get("action", "")))
        except Exception:
            pass

        if action_texts:
            actions_text = " ".join(action_texts)
            
        result = {
            "text_script_sentences": [
                {
                    "text": actions_text,
                    "fact_ids": fact_ids,
                    "action_ids": action_ids
                }
            ],
            "voice_script_sentences": [
                {
                    "text": actions_text,
                    "fact_ids": fact_ids,
                    "action_ids": action_ids
                }
            ]
        }
        return json.dumps(result)
