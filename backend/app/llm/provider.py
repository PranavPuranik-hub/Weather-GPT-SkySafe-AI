"""
LLM Provider factory and fallback logic.
"""
import logging
import os
from typing import Any, Dict, Tuple

from app.llm.client import LLMClient
from app.llm.gemini_client import GeminiClient
from app.llm.ollama_client import OllamaClient
from app.llm.template_client import TemplateClient

logger = logging.getLogger("app")

def get_llm_client() -> LLMClient:
    """
    Returns the primary configured LLM client based on LLM_PROVIDER.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        return GeminiClient()
    elif provider == "template":
        return TemplateClient()
    else:
        return OllamaClient()

def generate_with_fallback(system_prompt: str, user_prompt: str, json_schema: Dict[str, Any]) -> Tuple[str, str]:
    """
    Tries to generate with the primary provider.
    Falls back down the chain: primary -> ollama (if not primary) -> template.
    Returns (json_response_string, path_used).
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    clients = []

    if provider == "gemini":
        clients.append(("gemini", GeminiClient()))
        clients.append(("ollama_fallback", OllamaClient()))
    elif provider == "ollama":
        clients.append(("ollama", OllamaClient()))

    clients.append(("template", TemplateClient()))

    for path_name, client in clients:
        try:
            logger.info(f"Attempting generation with {path_name}")
            response_text = client.generate(system_prompt, user_prompt, json_schema)
            # Basic validation that it's JSON
            import json
            json.loads(response_text)
            return response_text, path_name
        except Exception as e:
            logger.warning(f"Generation failed with {path_name}: {e}")
            continue

    # Should never reach here if TemplateClient works
    return "{}", "error"
