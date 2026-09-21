"""
Agent package: Pluggable LLMProvider interface and drivers (Ollama, Gemini, Groq, Null).
"""
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

class NullProvider(LLMProvider):
    def generate(self, prompt: str) -> str:
        return "Deterministic template fallback response."
