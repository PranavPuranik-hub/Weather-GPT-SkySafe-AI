"""
Language, translation and multilingual action pack module.
"""
from app.lang.registry import (
    registry,
    LanguageInfo,
    get_language,
    get_all_languages,
    get_verified_languages
)
from app.lang.digits import to_target_digits, render_fact_slot
from app.lang.sms import format_emergency_sms, calculate_sms_segments
from app.lang.translator import translation_service, TranslationService

__all__ = [
    "registry",
    "LanguageInfo",
    "get_language",
    "get_all_languages",
    "get_verified_languages",
    "to_target_digits",
    "render_fact_slot",
    "format_emergency_sms",
    "calculate_sms_segments",
    "translation_service",
    "TranslationService",
]
