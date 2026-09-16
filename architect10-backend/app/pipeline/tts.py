"""
Step 4 — synthesize a dubbed voice track from translated text.

Uses ElevenLabs' multilingual model. Swap this module out for Azure
Neural TTS, Google Cloud TTS, or another provider if you need a language
ElevenLabs doesn't cover well — verify Swahili coverage directly with
whichever provider you pick, since language support varies and changes
over time.
"""
from pathlib import Path

import requests

from app.config import settings

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class TtsError(RuntimeError):
    pass


def synthesize_speech(text: str, lang_code: str, dest_path: Path) -> Path:
    if not settings.ELEVENLABS_API_KEY:
        raise TtsError("ELEVENLABS_API_KEY is not set.")

    voice_id = settings.ELEVENLABS_VOICE_IDS.get(lang_code)
    if not voice_id:
        raise TtsError(
            f"No ElevenLabs voice_id configured for language '{lang_code}' "
            "(set it in .env, e.g. ELEVENLABS_VOICE_ID_SW)."
        )

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.post(
        ELEVENLABS_TTS_URL.format(voice_id=voice_id),
        headers={
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": text,
            "model_id": settings.ELEVENLABS_MODEL_ID,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=120,
    )
    if resp.status_code != 200:
        raise TtsError(f"ElevenLabs TTS failed ({resp.status_code}): {resp.text[:300]}")

    dest_path.write_bytes(resp.content)
    return dest_path
