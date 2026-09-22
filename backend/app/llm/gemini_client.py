"""
Gemini client implementation via REST API.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict

from app.llm.client import LLMClient

logger = logging.getLogger("app")

class GeminiClient(LLMClient):
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = model
        self.timeout = 10.0
        
    def generate(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any]) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
            
        logger.info(f"GeminiClient generating with model {self.model}")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
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
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                candidates = data.get("candidates", [])
                if not candidates:
                    return "{}"
                content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                return content
        except urllib.error.HTTPError as e:
            if e.code == 429:
                logger.error("GeminiClient error: Quota exhausted or rate limited")
                raise Exception("ResourceExhausted")
            logger.error(f"GeminiClient HTTP error: {e}")
            raise
        except urllib.error.URLError as e:
            logger.error(f"GeminiClient URL error: {e}")
            raise
