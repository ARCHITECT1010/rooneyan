"""
Step 2 — transcribe the extracted audio with faster-whisper.

The model loads lazily and is cached process-wide, since loading it is the
slowest part of this step and every job after the first should reuse it.
"""
from pathlib import Path
from typing import List, Tuple

from faster_whisper import WhisperModel

from app.config import settings

_model = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )
    return _model


def transcribe(audio_path: Path) -> Tuple[str, str, List[dict]]:
    """
    Returns (full_text, detected_language_code, segments) where each segment
    is {"start": float, "end": float, "text": str}.
    """
    model = _get_model()
    segments_iter, info = model.transcribe(str(audio_path), vad_filter=True)

    segments = []
    text_parts = []
    for seg in segments_iter:
        segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
        text_parts.append(seg.text.strip())

    full_text = " ".join(text_parts).strip()
    return full_text, info.language, segments
