"""
Central configuration, loaded from environment variables (see .env.example).
Import `settings` anywhere you need a config value — don't read os.environ
directly elsewhere, so every setting stays discoverable from one place.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    # Storage
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data")).resolve()

    # Whisper (speech-to-text)
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    # Translation (Anthropic)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    # claude-sonnet-5 is the current Sonnet-class model as of writing this —
    # check https://docs.claude.com/en/docs/about-claude/models for the
    # latest lineup before deploying, model IDs change over time.
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    # Text-to-speech (ElevenLabs)
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_MODEL_ID: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

    # lang_code -> ElevenLabs voice_id
    ELEVENLABS_VOICE_IDS: dict = {
        "en": os.getenv("ELEVENLABS_VOICE_ID_EN", ""),
        "es": os.getenv("ELEVENLABS_VOICE_ID_ES", ""),
        "pt": os.getenv("ELEVENLABS_VOICE_ID_PT", ""),
        "pt-br": os.getenv("ELEVENLABS_VOICE_ID_PT_BR", ""),
        "fr": os.getenv("ELEVENLABS_VOICE_ID_FR", ""),
        "sw": os.getenv("ELEVENLABS_VOICE_ID_SW", ""),
    }

    # Binaries
    FFMPEG_BIN: str = os.getenv("FFMPEG_BIN", "ffmpeg")
    FFPROBE_BIN: str = os.getenv("FFPROBE_BIN", "ffprobe")

    # Concurrency
    # How many languages within a single job run at once (translate/TTS/mux
    # are I/O-bound, so this is mostly limited by your API rate limits).
    LANGUAGE_CONCURRENCY: int = int(os.getenv("LANGUAGE_CONCURRENCY", "3"))
    # How many jobs (i.e. HTTP requests) run at once across the whole
    # process — see main.py. Raise this once you've confirmed a single job
    # runs cleanly; each concurrent job needs its own yt-dlp download and,
    # if WHISPER_DEVICE=cpu, competes for the same CPU during transcription.
    JOB_CONCURRENCY: int = int(os.getenv("JOB_CONCURRENCY", "2"))


settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

# Human-readable names, used in translation prompts and API responses
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese (Portugal)",
    "pt-br": "Portuguese (Brazil)",
    "fr": "French",
    "sw": "Swahili",
}
