"""
Step 1 — download the source video.

yt-dlp covers TikTok, Instagram, Facebook, Dailymotion, and X/Twitter, but
coverage for a given platform can change as they update their sites, and
some content (private accounts, age-gated posts, some Facebook/Instagram
videos) needs authenticated cookies to fetch at all.

IMPORTANT: only run this against content you have the rights to dub and
redistribute — each of these platforms' Terms of Service restricts
downloading, and copyright in the underlying video stays with its creator
regardless of what a tool lets you technically do.
"""
from pathlib import Path

import yt_dlp

from app.config import settings


class DownloadError(RuntimeError):
    pass


def download_video(url: str, dest_dir: Path) -> Path:
    """Download `url` into `dest_dir` and return the path to the video file."""
    if not url.startswith(("http://", "https://")):
        raise DownloadError(f"'{url}' doesn't look like a video URL (expected http(s)://...).")

    dest_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(dest_dir / "source.%(ext)s")

    ydl_opts = {
        "outtmpl": out_template,
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # Without this, yt-dlp's merge/remux step silently falls back to
        # whatever "ffmpeg" resolves to on PATH, ignoring a custom FFMPEG_BIN.
        "ffmpeg_location": settings.FFMPEG_BIN,
        # If a platform needs login to fetch a given video, point this at a
        # cookies.txt you've exported from a logged-in browser session:
        # "cookiefile": "cookies.txt",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # yt-dlp raises several exception types depending
        # on the failure (unsupported URL, extractor error, network error,
        # geo-block, login required...) — normalize all of them to DownloadError
        # so callers only need to handle one type.
        raise DownloadError(f"Could not download video: {exc}") from exc

    candidates = sorted(dest_dir.glob("source.*"))
    if not candidates:
        raise DownloadError("Download reported success but no output file was found.")
    return candidates[0]
