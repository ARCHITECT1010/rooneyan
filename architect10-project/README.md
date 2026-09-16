# Architect 10

Paste a video link, pick target languages, get it back dubbed.

- **`architect10.html`** — the frontend. Open it directly in a browser.
- **`backend/`** — the FastAPI dubbing pipeline. See `backend/README.md` for
  full setup (ffmpeg, API keys, running it).

## Quick start

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your API keys
uvicorn app.main:app --reload
```

Then open `architect10.html` in a browser — it defaults to
`http://localhost:8000` as the backend URL.

Want to check the frontend is wired up correctly before touching real API
keys or ffmpeg? Run `python3 backend/mock_server.py` instead — it fakes the
whole pipeline over the same API contract.

&copy; Architect 10. All rights reserved.
