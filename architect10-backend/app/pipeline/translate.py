"""
Step 3 — translate the transcript into a target language, phrased for
someone to read aloud as a dub rather than for a subtitle file.
"""
import anthropic

from app.config import settings, LANGUAGE_NAMES


class TranslationError(RuntimeError):
    pass


_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise TranslationError("ANTHROPIC_API_KEY is not set.")
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def translate_text(text: str, target_lang_code: str) -> str:
    if target_lang_code not in LANGUAGE_NAMES:
        raise TranslationError(f"Unsupported language code: {target_lang_code}")

    target_name = LANGUAGE_NAMES[target_lang_code]
    client = _get_client()

    try:
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=2000,
            system=(
                "You translate video dialogue for dubbing. Translate the "
                f"user's text into {target_name}, in natural spoken language "
                "a voice actor would read aloud. Keep roughly the same "
                "length and pacing as the original so the dub can be timed "
                "against it. Reply with only the translated text — no "
                "notes, no quotation marks, no preamble."
            ),
            messages=[{"role": "user", "content": text}],
        )
    except anthropic.APIError as exc:
        raise TranslationError(f"Translation request failed: {exc}") from exc

    return "".join(block.text for block in response.content if block.type == "text").strip()
