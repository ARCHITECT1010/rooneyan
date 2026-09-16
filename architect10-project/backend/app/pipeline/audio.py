"""
Audio helpers built on the ffmpeg/ffprobe command-line tools.
"""
import json
import subprocess
from pathlib import Path

from app.config import settings


class FfmpegError(RuntimeError):
    pass


def _run(cmd: list) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise FfmpegError(result.stderr.strip() or f"Command failed: {' '.join(cmd)}")
    return result.stdout


def extract_audio(video_path: Path, dest_path: Path) -> Path:
    """Extract mono 16kHz WAV audio from a video — the format faster-whisper wants."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    _run([
        settings.FFMPEG_BIN, "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(dest_path),
    ])
    return dest_path


def get_duration_seconds(media_path: Path) -> float:
    out = _run([
        settings.FFPROBE_BIN, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(media_path),
    ])
    data = json.loads(out)
    return float(data["format"]["duration"])
