"""
Wires the individual steps into one job: download once, transcribe once,
then fan out into translate -> synthesize -> mux per target language.

Languages run concurrently (bounded by LANGUAGE_CONCURRENCY) since each
one is dominated by waiting on network calls (translation, TTS) rather
than CPU — running them one at a time would leave a multi-language job
idle most of the time for no benefit.
"""
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict

from app.config import settings
from app.models import JobStatus, LanguageResult, Stage
from app.pipeline.download import download_video, DownloadError
from app.pipeline.audio import extract_audio, FfmpegError
from app.pipeline.transcribe import transcribe
from app.pipeline.translate import translate_text, TranslationError
from app.pipeline.tts import synthesize_speech, TtsError
from app.pipeline.mux import merge_audio_video


def _process_language(lang_code: str, result: LanguageResult, full_text: str,
                       video_path: Path, job_dir: Path) -> None:
    """Runs translate -> synthesize -> mux for one language, updating `result`
    in place. Each call only touches its own LanguageResult, so this is safe
    to run concurrently across languages."""
    try:
        result.stage = Stage.TRANSLATING
        translated = translate_text(full_text, lang_code)

        result.stage = Stage.SYNTHESIZING
        dub_audio_path = synthesize_speech(
            translated, lang_code, job_dir / f"dub_{lang_code}.mp3"
        )

        result.stage = Stage.MUXING
        out_path = merge_audio_video(
            video_path, dub_audio_path, job_dir / f"dubbed_{lang_code}.mp4"
        )

        result.output_path = str(out_path)
        result.stage = Stage.DONE
    except (TranslationError, TtsError, FfmpegError) as exc:
        result.stage = Stage.FAILED
        result.error = str(exc)
    except Exception as exc:  # noqa: BLE001 — one language's bug shouldn't crash the job
        result.stage = Stage.FAILED
        result.error = f"Unexpected error: {exc}"


def run_dub_job(job_id: str, jobs: Dict[str, JobStatus]) -> None:
    job = jobs[job_id]
    job_dir = settings.DATA_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Download
        job.stage = Stage.DOWNLOADING
        video_path = download_video(job.source_url, job_dir)

        # 2. Extract audio
        job.stage = Stage.EXTRACTING_AUDIO
        source_audio_path = extract_audio(video_path, job_dir / "source_audio.wav")

        # 3. Transcribe (once, reused for every target language)
        job.stage = Stage.TRANSCRIBING
        full_text, detected_lang, _segments = transcribe(source_audio_path)
        job.transcript_preview = full_text[:280]

        if not full_text.strip():
            raise RuntimeError("No speech detected in the source video's audio track.")

        # 4-6. Per language: translate -> synthesize -> mux, in parallel
        with ThreadPoolExecutor(max_workers=settings.LANGUAGE_CONCURRENCY) as pool:
            futures = [
                pool.submit(_process_language, lang_code, result, full_text, video_path, job_dir)
                for lang_code, result in job.languages.items()
            ]
            for f in futures:
                f.result()  # re-raises anything _process_language didn't already catch

        job.stage = Stage.DONE

    except (DownloadError, FfmpegError) as exc:
        job.stage = Stage.FAILED
        job.error = str(exc)
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors to the client
        job.stage = Stage.FAILED
        job.error = f"{exc}\n{traceback.format_exc()}"
