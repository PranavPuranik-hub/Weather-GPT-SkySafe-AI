"""
Language Registry for SkySafe AI.
Loads language configuration from languages.yaml.
"""
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

CONFIG_PATH = Path(__file__).parent / "languages.yaml"


class TTSVoiceConfig(BaseModel):
    sarvam: str = ""
    edge: str = ""
    gtts: str = ""


class LanguageInfo(BaseModel):
    code: str
    name: str
    native_name: str
    script: str
    rtl: bool = False
    verified: bool = False
    tts_voice: TTSVoiceConfig = Field(default_factory=TTSVoiceConfig)


class LanguageRegistry:
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or CONFIG_PATH
        self._languages: Dict[str, LanguageInfo] = {}
        self._load()

    def _load(self) -> None:
        if not self.config_file.exists():
            return
        with open(self.config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for entry in data.get("languages", []):
            lang = LanguageInfo(**entry)
            self._languages[lang.code] = lang

    def get(self, code: str) -> Optional[LanguageInfo]:
        """Get language info by code."""
        return self._languages.get(code.lower())

    def get_all(self) -> List[LanguageInfo]:
        """Return all configured languages."""
        return list(self._languages.values())

    def get_verified(self) -> List[LanguageInfo]:
        """Return only verified languages (for UI presentation by default)."""
        return [l for l in self._languages.values() if l.verified]

    def is_verified(self, code: str) -> bool:
        """Check if a language code is marked verified."""
        lang = self.get(code)
        return bool(lang and lang.verified)


registry = LanguageRegistry()


def get_language(code: str) -> Optional[LanguageInfo]:
    return registry.get(code)


def get_all_languages() -> List[LanguageInfo]:
    return registry.get_all()


def get_verified_languages() -> List[LanguageInfo]:
    return registry.get_verified()
