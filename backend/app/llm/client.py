"""
Base LLM Client interface for SkySafe AI.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMClient(ABC):
    """
    Abstract base class for all LLM providers.
    """
    
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any]) -> str:
        """
        Generate a response given a system prompt, user prompt, and an expected JSON schema.
        Returns the raw string output (expected to be parseable JSON).
        Raises an exception on timeout or failure.
        """
        pass
