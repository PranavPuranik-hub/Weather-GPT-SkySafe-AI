"""
Pure-Python Emergency Broadcast Chime Generator.
Produces a distinct two-tone alert chime (D5 + A5) for lead-in audio notes.
"""
import io
import math
import struct
import wave


def generate_emergency_chime(sample_rate: int = 16000) -> bytes:
    """
    Generate a 16-bit mono PCM WAV alert chime of ~340ms duration.
    Tone 1: 587.33 Hz (D5) for 120ms with smooth envelope.
    Tone 2: 880.00 Hz (A5) for 220ms with exponential decay.
    """
    duration1 = 0.12
    duration2 = 0.22
    buf = io.BytesIO()

    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        # Tone 1
        n_samples1 = int(sample_rate * duration1)
        for i in range(n_samples1):
            t = i / sample_rate
            env = math.sin(math.pi * (i / n_samples1))
            sample = int(32767 * 0.35 * env * math.sin(2 * math.pi * 587.33 * t))
            wav.writeframes(struct.pack("<h", sample))

        # Tone 2
        n_samples2 = int(sample_rate * duration2)
        for i in range(n_samples2):
            t = i / sample_rate
            env = math.exp(-4.0 * t)
            sample = int(32767 * 0.45 * env * math.sin(2 * math.pi * 880.0 * t))
            wav.writeframes(struct.pack("<h", sample))

    return buf.getvalue()
