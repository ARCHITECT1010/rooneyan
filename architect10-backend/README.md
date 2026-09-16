# Architect 10 — dubbing backend

Downloads a video from a link, transcribes the speech, translates it, generates
a dubbed voice track per target language, and muxes each one back onto the
video. Pairs with the `architect10.html` frontend prototype from earlier —
point its "Start dubbing" flow at this API instead of the simulated pipeline.

## Before you run this against real content

yt-dlp can pull video from TikTok, Instagram, Facebook, Dailymotion, and
X/Twitter, but each platform's Terms of Service restricts downloading and
redistributing content, and the copyright in a video stays with its creator
regardless of what a tool lets you technically do. Only run this against
videos you own, have a license for, or otherwise have clear rights to dub
and redistribute — and check each platform's current ToS yourself, since
they change.

## Try it in 10 seconds (no API keys, no ffmpeg)

`mock_server.py` is a dependency-free stand-in that speaks the exact same
API — same routes, same JSON shapes, same stage names — but fakes the
pipeline instead of running it, including one language deliberately
"failing" so you can see that state too. Good for confirming the frontend
is wired up correctly before installing the real dependencies:

```bash
python3 mock_server.py
```

Then open `architect10.html`, leave the backend URL as `http://localhost:8000`,
and run a job. Swap to the real `uvicorn app.main:app --reload` server once
you're ready to process actual video.

## Setup

1. **Install ffmpeg** (system package, not pip) — `ffmpeg -version` should work in your shell.
2. **Python deps:**
   ```bash
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Copy `.env.example` to `.env`** and fill in:
   - `ANTHROPIC_API_KEY` — used to translate each transcript
   - `ELEVENLABS_API_KEY` and one `ELEVENLABS_VOICE_ID_*` per language you
     want to support — used to synthesize the dubbed voice. Confirm each
     voice actually supports the target language in ElevenLabs' voice
     library before relying on it, Swahili in particular is worth
     double-checking since coverage varies by provider and changes over time.
   - faster-whisper runs locally and needs no API key, but will download
     the Whisper model weights the first time it runs.
4. **Run it:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Using it

```bash
# Start a job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.tiktok.com/@user/video/123", "languages": ["en", "es", "sw"]}'
# -> {"job_id": "a1b2c3d4e5f6"}

# Poll status
curl http://localhost:8000/jobs/a1b2c3d4e5f6

# Once a language's stage is "done", download it
curl -OJ http://localhost:8000/jobs/a1b2c3d4e5f6/download/es
```

Supported language codes: `en`, `es`, `pt`, `pt-br`, `fr`, `sw` (see
`app/config.py:LANGUAGE_NAMES` to add more — you'll also need an ElevenLabs
voice for each one you add).

## How it works

```
download.py    yt-dlp pulls the source video
audio.py       ffmpeg extracts mono 16kHz audio for the speech model
transcribe.py  faster-whisper turns it into text (once, source language)
translate.py   Claude translates the transcript per target language
tts.py         ElevenLabs turns the translation into a voice track
mux.py         ffmpeg time-stretches the dub to match the clip's length,
               then replaces the original audio track with it
orchestrator.py   runs all of the above per job, updates job status as it goes
main.py        FastAPI wrapper: POST /jobs, GET /jobs/{id}, download endpoint
```

## Known limitations, worth knowing before you rely on this

- **Whole-clip timing, not lip sync.** The dub is stretched or compressed to
  match the source clip's total duration, not aligned word-by-word. Fine for
  voiceover-style content; noticeable on tight lip-synced dialogue. Real lip
  sync would mean generating and timing audio per transcript segment
  (`transcribe.py` already returns segment-level timestamps to build on).
- **One voice per language, for the whole clip.** No speaker diarization —
  if the source has multiple speakers, they'll all come out in one voice.
- **In-memory job store.** `JOBS` in `main.py` resets on restart and won't
  scale past one process. Swap in Redis or a database before running this
  as a real service with more than a couple of concurrent users. Job status
  is also mutated from background threads without a lock — fine at small
  scale (Python's GIL protects individual attribute writes), but worth
  knowing if you see occasional stale reads under heavy concurrent polling.
- **No auth, no rate limiting, no size caps** on the API as written — add
  these before exposing it publicly.
- **Languages within a job run in parallel** (`LANGUAGE_CONCURRENCY` in
  `.env`, default 3) since translation and TTS are mostly spent waiting on
  network calls. **Jobs across different requests** are capped by
  `JOB_CONCURRENCY` (default 2) — a job beyond that limit sits at `queued`
  until a slot frees up, which is expected, not a bug. Raise both once
  you've confirmed a single job runs cleanly end to end; check your
  Anthropic and ElevenLabs rate limits before raising `LANGUAGE_CONCURRENCY`
  much further, since that's what will actually cap you.
- **Long or dense-speech source videos** take longer — Whisper transcription
  and TTS both scale roughly with clip length.

## Swapping providers

- **Translation:** `translate.py` is a single function
  (`translate_text(text, target_lang_code)`) — swap in DeepL, Google
  Translate, or another LLM by replacing its body.
- **TTS:** `tts.py` is similarly a single function
  (`synthesize_speech(text, lang_code, dest_path)`) — swap in Azure Neural
  TTS, Google Cloud TTS, or a local/open-source option like Coqui TTS if you
  need different language coverage, cost, or to avoid a cloud dependency.
