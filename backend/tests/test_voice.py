from app.voice import text_to_speech


def test_text_to_speech():
    audio = text_to_speech("Warning: Heavy rainfall expected.")
    assert isinstance(audio, bytes)
    assert len(audio) > 0
