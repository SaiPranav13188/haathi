"""Speech-to-text adapters. The browser's Web Speech API (te-IN / hi-IN / en-IN) is the default on-device path;
the server path uses Gemini audio input. An AI4Bharat IndicConformer adapter can be plugged in here (see
eval/asr_compare.py for the WER experiment)."""
from __future__ import annotations

from .. import llm

LANG = {"te": "Telugu", "hi": "Hindi", "en": "Indian English"}


async def transcribe(audio: bytes, mime: str, lang: str) -> str | None:
    if not llm.available():
        return None
    text = await llm.complete(
        f"Transcribe this speech exactly. The speaker most likely uses {LANG.get(lang, 'Telugu')}, but may speak Telugu, "
        "Hindi or English, or mix them. Write Telugu in Telugu script, Hindi in Devanagari and English words in English. "
        "Write numbers as digits. If there is no speech, reply with nothing. Reply with only the transcript.",
        audio=(audio, mime), cache=False)
    return text.strip().strip('"') if text else ""
