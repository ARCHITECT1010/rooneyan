"""
Step 5 — stretch the dubbed audio to match the source video's duration,
then mux it in, replacing the original audio track.

This is a whole-clip duration match, not per-word lip sync — good enough
for talking-head / voiceover style short-form video, not for tight
lip-synced dialogue. If you need real lip sync later, this is the module
to replace with per-segment timing against the transcript's segment list.
"""
import subprocess
from pathlib import Path

from app.config import settings
from app.pipeline.audio import get_duration_seconds, FfmpegError


def _run(cmd: list) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise FfmpegError(result.stderr.strip() or f"Command failed: {' '.join(cmd)}")


def _atempo_chain(factor: float) -> str:
    """ffmpeg's atempo filter only accepts 0.5–2.0 per instance; chain several
    to reach factors outside that range."""
    filters = []
    remaining = factor
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.4f}")
    return ",".join(filters)


def merge_audio_video(video_path: Path, dub_audio_path: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    video_duration = get_duration_seconds(video_path)
    dub_duration = get_duration_seconds(dub_audio_path)

    # speed the dub up/down so it fills the same runtime as the source clip
    tempo_factor = max(dub_duration / video_duration, 0.25) if video_duration > 0 else 1.0
    tempo_factor = min(tempo_factor, 4.0)

    filter_chain = _atempo_chain(tempo_factor)

    _run([
        settings.FFMPEG_BIN, "-y",
        "-i", str(video_path),
        "-i", str(dub_audio_path),
        "-filter_complex", f"[1:a]{filter_chain}[a]",
        "-map", "0:v:0",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(out_path),
    ])
    return out_path
