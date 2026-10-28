"""Text-to-speech. Answers are read aloud with the browser's speechSynthesis (te-IN / hi-IN / en-IN voices);
this module is the server-side fallback hook for AI4Bharat Indic TTS when a voice is missing on the device."""
from __future__ import annotations


def available() -> bool:
    return False
