"""
Voice module for audio synthesis, caching, and playback.
"""
from app.voice.chime import generate_emergency_chime
from app.voice.models import VoiceRequest, VoiceResponse
from app.voice.synthesizer import AUDIO_CACHE_DIR, VoiceSynthesizer, voice_synthesizer


def text_to_speech(text: str, lang: str = "hi") -> bytes:
    """Synthesize voice note (max 30 seconds), returning raw audio bytes."""
    res = voice_synthesizer.synthesize(text, lang=lang)
    return res.get("audio_bytes", b"")


__all__ = [
    "text_to_speech",
    "generate_emergency_chime",
    "voice_synthesizer",
    "VoiceSynthesizer",
    "VoiceRequest",
    "VoiceResponse",
    "AUDIO_CACHE_DIR",
]
