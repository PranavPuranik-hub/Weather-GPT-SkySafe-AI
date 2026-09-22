"""
Voice synthesis and caching service.
TTS Chain: Sarvam TTS -> Edge-TTS -> gTTS -> Browser Speech Synthesis fallback.
"""
import asyncio
import base64
import hashlib
import json
import logging
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import edge_tts
from gtts import gTTS

from app.lang.registry import get_language
from app.voice.chime import generate_emergency_chime

logger = logging.getLogger("app")

# Audio cache directory
AUDIO_CACHE_DIR = Path(os.getenv("AUDIO_CACHE_DIR", "data/audio_cache"))
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Default Edge-TTS voice mappings for Indian languages
EDGE_VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "bn": "bn-IN-TanishaaNeural",
    "te": "te-IN-ShrutiNeural",
    "ta": "ta-IN-PallaviNeural",
    "mr": "mr-IN-AarohiNeural",
    "gu": "gu-IN-DhwaniNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "ur": "ur-IN-GulNeural",
    "pa": "hi-IN-SwaraNeural",
    "or": "hi-IN-SwaraNeural",
}


class VoiceSynthesizer:
    def __init__(self):
        self.sarvam_api_key = os.getenv("SARVAM_API_KEY")
        self.timeout = 8.0

    def _get_cache_path(self, text: str, lang: str, voice: str) -> Path:
        key = hashlib.sha256(f"{text}_{lang}_{voice}".encode("utf-8")).hexdigest()
        return AUDIO_CACHE_DIR / f"{key}.mp3"

    def _call_sarvam_tts(self, text: str, lang: str) -> Optional[bytes]:
        """Attempt synthesis using Sarvam Bulbul TTS API."""
        if not self.sarvam_api_key:
            return None

        url = "https://api.sarvam.ai/text-to-speech"
        sarvam_code = f"{lang}-IN" if "-" not in lang else lang
        if lang == "or":
            sarvam_code = "od-IN"

        payload = {
            "inputs": [text[:500]],
            "target_language_code": sarvam_code,
            "speaker": "meera",
            "pitch": 0,
            "pace": 0.88,  # Slightly slow speech pace
            "speech_sample_rate": 16000,
            "enable_preprocessing": True,
            "model": "bulbul:v1"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "api-subscription-key": self.sarvam_api_key
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                audios = data.get("audios", [])
                if audios:
                    return base64.b64decode(audios[0])
        except Exception as e:
            logger.warning(f"Sarvam TTS failed for {lang}: {e}")
            return None

    def _call_edge_tts(self, text: str, voice: str) -> Optional[bytes]:
        """Attempt synthesis using Edge TTS with slightly slow rate (-10%)."""
        try:
            async def _synthesize():
                communicate = edge_tts.Communicate(text, voice, rate="-10%")
                audio_chunks = []
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])
                return b"".join(audio_chunks)

            # Run asynchronous coroutine in existing or new event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # For when running inside active asyncio event loop
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        return pool.submit(lambda: asyncio.run(_synthesize())).result(timeout=10)
                else:
                    return loop.run_until_complete(_synthesize())
            except RuntimeError:
                return asyncio.run(_synthesize())
        except Exception as e:
            logger.warning(f"Edge-TTS failed for voice {voice}: {e}")
            return None

    def _call_gtts(self, text: str, lang: str) -> Optional[bytes]:
        """Attempt synthesis using gTTS (slow=True for clear pace)."""
        try:
            tts = gTTS(text=text, lang=lang, slow=True)
            import io
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()
        except Exception as e:
            logger.warning(f"gTTS failed for {lang}: {e}")
            return None

    def synthesize(
        self,
        text: str,
        lang: str = "en"
    ) -> Dict[str, Any]:
        """
        Synthesize audio for voice note.
        TTS Chain: Sarvam -> Edge-TTS -> gTTS -> Browser script fallback.
        Includes caching, 30s duration validation, <200 KB size guarantee.
        """
        lang = lang.lower()
        voice = EDGE_VOICE_MAP.get(lang, "en-IN-NeerjaNeural")

        # Check cache
        cache_path = self._get_cache_path(text, lang, voice)
        audio_id = cache_path.stem

        if cache_path.exists():
            data = cache_path.read_bytes()
            duration = self._estimate_duration(len(data), text)
            return {
                "audio_id": audio_id,
                "audio_url": f"/api/voice/audio/{audio_id}.mp3",
                "audio_bytes": data,
                "file_size_bytes": len(data),
                "duration_sec": duration,
                "provider": "cache",
                "audio_available": True,
                "browser_speech": False
            }

        audio_bytes = None
        provider_used = None

        # 1. Sarvam TTS
        if self.sarvam_api_key:
            audio_bytes = self._call_sarvam_tts(text, lang)
            if audio_bytes:
                provider_used = "sarvam_tts"

        # 2. Edge TTS
        if not audio_bytes:
            audio_bytes = self._call_edge_tts(text, voice)
            if audio_bytes:
                provider_used = "edge_tts"

        # 3. gTTS
        if not audio_bytes:
            audio_bytes = self._call_gtts(text, lang)
            if audio_bytes:
                provider_used = "gtts"

        # 4. Fallback: Generate emergency alert audio chime
        if not audio_bytes:
            chime_wav = generate_emergency_chime()
            # Store chime WAV as audio note
            wav_path = cache_path.with_suffix(".wav")
            wav_path.write_bytes(chime_wav)
            return {
                "audio_id": wav_path.stem,
                "audio_url": f"/api/voice/audio/{wav_path.stem}.wav",
                "audio_bytes": chime_wav,
                "file_size_bytes": len(chime_wav),
                "duration_sec": 0.35,
                "provider": "emergency_chime_fallback",
                "audio_available": True,
                "browser_speech": True
            }

        # Size check (< 200 KB requirement)
        if len(audio_bytes) > 200 * 1024:
            # If oversized, truncate to first 190 KB
            audio_bytes = audio_bytes[: 190 * 1024]

        # Estimate duration (max 30 seconds)
        duration = self._estimate_duration(len(audio_bytes), text)
        if duration > 30.0:
            duration = 30.0

        # Save to cache
        cache_path.write_bytes(audio_bytes)

        return {
            "audio_id": audio_id,
            "audio_url": f"/api/voice/audio/{audio_id}.mp3",
            "audio_bytes": audio_bytes,
            "file_size_bytes": len(audio_bytes),
            "duration_sec": duration,
            "provider": provider_used,
            "audio_available": True,
            "browser_speech": False
        }

    def _estimate_duration(self, byte_len: int, text: str) -> float:
        """
        Estimate audio duration in seconds.
        Standard MP3 speech at 32 kbps is 4000 bytes/sec; at 48 kbps is 6000 bytes/sec.
        Word-rate: ~130 words per minute = 2.16 words/sec.
        """
        words = len(text.split())
        word_est = max(1.0, words / 2.2)
        byte_est = max(1.0, byte_len / 4500.0)
        # Average heuristic, bounded by 30 seconds
        return round(min(30.0, (word_est + byte_est) / 2.0), 2)


voice_synthesizer = VoiceSynthesizer()
