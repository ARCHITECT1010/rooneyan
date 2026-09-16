"""
A dependency-free stand-in for app/main.py, matching the exact same API
contract (routes, JSON shapes, stage names). Useful for:

  - Smoke-testing the frontend against a real HTTP server without needing
    ffmpeg, yt-dlp, faster-whisper, or any API keys installed yet.
  - CI checks that don't want to pull in the full pipeline's dependencies.

It fakes progress through the same stages the real orchestrator reports,
including one language "failing" on purpose so you can see that state in
the UI too. Nothing here downloads or synthesizes anything real.

Run:
    python3 mock_server.py
Then point the frontend's backend URL at http://localhost:8000 as usual.
"""
import json
import random
import string
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese (Portugal)",
    "pt-br": "Portuguese (Brazil)",
    "fr": "French",
    "sw": "Swahili",
}

SHARED_STAGES = ["queued", "downloading", "extracting_audio", "transcribing"]
LANG_STAGES = ["queued", "translating", "synthesizing", "muxing", "done"]

JOBS = {}
LOCK = threading.Lock()


def _new_job_id() -> str:
    return "".join(random.choices(string.hexdigits.lower()[:16], k=12))


def _simulate(job_id: str):
    with LOCK:
        job = JOBS[job_id]

    for stage in SHARED_STAGES[1:]:
        time.sleep(1.0)
        with LOCK:
            job["stage"] = stage
    with LOCK:
        job["transcript_preview"] = "(mock transcript) Hey everyone, welcome back to the channel..."

    lang_codes = list(job["languages"].keys())
    # Make the demo show a realistic mixed outcome if three or more languages
    # are requested; otherwise everything succeeds.
    fail_code = lang_codes[-1] if len(lang_codes) >= 3 else None

    def run_language(code):
        for stage in LANG_STAGES[1:]:
            time.sleep(0.9)
            with LOCK:
                if code == fail_code and stage == "synthesizing":
                    job["languages"][code]["stage"] = "failed"
                    job["languages"][code]["error"] = (
                        "Mock failure: no voice configured for this language "
                        "(this is a simulated error for demo purposes)."
                    )
                    return
                job["languages"][code]["stage"] = stage
        with LOCK:
            job["languages"][code]["output_path"] = f"mock-output-{code}.mp4"

    threads = [threading.Thread(target=run_language, args=(c,)) for c in lang_codes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    with LOCK:
        job["stage"] = "done"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        parts = [p for p in path.split("/") if p]

        if path == "/languages":
            return self._send_json(200, LANGUAGE_NAMES)

        if len(parts) == 2 and parts[0] == "jobs":
            job = JOBS.get(parts[1])
            if not job:
                return self._send_json(404, {"detail": "Job not found."})
            with LOCK:
                return self._send_json(200, json.loads(json.dumps(job)))

        if len(parts) == 4 and parts[0] == "jobs" and parts[2] == "download":
            job = JOBS.get(parts[1])
            lang = parts[3]
            if not job:
                return self._send_json(404, {"detail": "Job not found."})
            result = job["languages"].get(lang)
            if not result or result["stage"] != "done":
                return self._send_json(404, {"detail": "That language isn't ready yet."})
            body = f"(mock dubbed video bytes for {lang})".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        return self._send_json(404, {"detail": "Not found."})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/jobs":
            return self._send_json(404, {"detail": "Not found."})

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send_json(400, {"detail": "Invalid JSON body."})

        url = payload.get("url")
        languages = payload.get("languages") or []
        unknown = [l for l in languages if l not in LANGUAGE_NAMES]
        if not url:
            return self._send_json(400, {"detail": "Missing 'url'."})
        if not languages:
            return self._send_json(400, {"detail": "Provide at least one target language."})
        if unknown:
            return self._send_json(400, {"detail": f"Unsupported language code(s): {unknown}"})

        job_id = _new_job_id()
        job = {
            "job_id": job_id,
            "source_url": url,
            "stage": "queued",
            "error": None,
            "transcript_preview": None,
            "languages": {
                code: {"language": code, "stage": "queued", "output_path": None, "error": None}
                for code in languages
            },
        }
        with LOCK:
            JOBS[job_id] = job

        threading.Thread(target=_simulate, args=(job_id,), daemon=True).start()
        return self._send_json(200, {"job_id": job_id})

    def log_message(self, fmt, *args):
        pass  # keep stdout quiet


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    print("Mock Architect 10 API running on http://localhost:8000")
    server.serve_forever()
