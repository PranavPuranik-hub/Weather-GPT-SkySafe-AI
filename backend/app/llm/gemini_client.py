"""
Gemini client implementation via REST API.
"""
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.llm.client import LLMClient

logger = logging.getLogger("app")

class GeminiClient(LLMClient):
    def __init__(self, model: str = "gemini-3.6-flash"):
        self.api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.timeout = float(getattr(settings, "GEMINI_TIMEOUT", 8.0) or os.getenv("GEMINI_TIMEOUT", "8.0"))
        # Candidate models ordered by capability and confirmed availability
        candidates = [model, getattr(settings, "GEMINI_MODEL", "gemini-3.6-flash"), "gemini-3.6-flash", "gemma-4-26b-a4b-it"]
        self.candidate_models = [m for m in dict.fromkeys(candidates) if m]
        self.rate_limited_until: Dict[str, float] = {}

    def generate(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any]) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        ssl_ctx = None
        try:
            import ssl
            ssl_ctx = ssl._create_unverified_context()
        except Exception:
            ssl_ctx = None

        import time
        for m in self.candidate_models:
            if time.time() < self.rate_limited_until.get(m, 0.0):
                continue

            logger.info(f"GeminiClient generating with model {m}")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"

            payload = {
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_prompt}]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": json_schema
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            try:
                with urllib.request.urlopen(req, context=ssl_ctx, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                        if content and content.strip():
                            return content.strip()
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    logger.warning(f"Model {m} rate limited (429). Setting 60s cooldown.")
                    self.rate_limited_until[m] = time.time() + 60.0
                logger.warning(f"Model {m} HTTP error {e.code}")
                continue
            except Exception as e:
                logger.warning(f"Model {m} failed: {e}")
                continue

        return "{}"

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[Any] = None,
        max_output_tokens: int = 800
    ) -> str:
        """
        Generate conversational freeform text using Gemini / Gemma REST API with multi-model fallback.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        ssl_ctx = None
        try:
            import ssl
            ssl_ctx = ssl._create_unverified_context()
        except Exception:
            ssl_ctx = None

        contents = []
        if history and isinstance(history, list):
            for item in history[-6:]:
                role = "user" if item.get("role") == "user" else "model"
                text = item.get("text", "")
                if text:
                    contents.append({"role": role, "parts": [{"text": text}]})

        contents.append({"role": "user", "parts": [{"text": user_prompt}]})

        import time
        for m in self.candidate_models:
            if time.time() < self.rate_limited_until.get(m, 0.0):
                continue

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"

            payload = {
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": max_output_tokens,
                    "temperature": 0.7,
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            try:
                with urllib.request.urlopen(req, context=ssl_ctx, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if content and len(content.strip()) > 1:
                            import re
                            text = re.sub(r"<thought>.*?</thought>", "", content, flags=re.DOTALL).strip()
                            if re.search(r"^\s*\*\s*(User|Goal|Intent|Persona|Constraints|Check|Instruction|Joke)", text, re.MULTILINE):
                                quotes = re.findall(r'"([^"\n]{6,})"', text)
                                if quotes:
                                    filtered = [q for q in quotes if q.strip().lower() != user_prompt.strip().lower()]
                                    if filtered:
                                        text = filtered[-1]
                                    else:
                                        text = quotes[-1]
                                else:
                                    non_bullet = [l.strip() for l in text.split("\n") if l.strip() and not l.strip().startswith("*")]
                                    if non_bullet:
                                        text = "\n".join(non_bullet)
                            return text.strip()
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    logger.warning(f"Model {m} rate limited (429). Setting 60s cooldown.")
                    self.rate_limited_until[m] = time.time() + 60.0
                logger.warning(f"Model {m} HTTP error {e.code}")
                continue
            except Exception as e:
                logger.warning(f"Model {m} failed: {e}")
                continue

        return ""


gemini_client = GeminiClient()

