"""
Ollama client implementation.
"""
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict

from app.llm.client import LLMClient

logger = logging.getLogger("app")

class OllamaClient(LLMClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = None):
        self.base_url = base_url.rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.timeout = 10.0  # 10s timeout

    def generate(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any]) -> str:
        logger.info(f"OllamaClient generating with model {self.model}")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "format": json_schema,
            "stream": False
        }

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data.get("message", {}).get("content", "{}")
        except urllib.error.URLError as e:
            logger.error(f"OllamaClient error: {e}")
            raise
