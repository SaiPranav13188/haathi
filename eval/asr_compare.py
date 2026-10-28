"""ASR comparison (Prompt 8): word error rate per engine on recorded clips.

Put clips in eval/asr_clips/<lang>/<name>.webm|wav with the reference transcript in <name>.txt
(20 per language). Engines: Gemini audio input (needs GEMINI_API_KEY); add AI4Bharat IndicConformer by
implementing `ai4bharat()` below."""
from __future__ import annotations

import asyncio
from pathlib import Path

from harness import REPORTS, ROOT

from app.speech.asr import transcribe

CLIPS = ROOT / "eval" / "asr_clips"


def wer(ref: str, hyp: str) -> float:
    r, h = ref.split(), hyp.split()
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (r[i - 1] != h[j - 1]))
    return d[-1][-1] / max(len(r), 1)


async def main() -> None:
    rows = []
    for lang_dir in sorted(p for p in CLIPS.glob("*") if p.is_dir()):
        clips = [p for p in lang_dir.iterdir() if p.suffix in {".wav", ".webm", ".mp3", ".m4a"}]
        scores = []
        for c in clips:
            ref = c.with_suffix(".txt").read_text(encoding="utf-8").strip()
            mime = {".wav": "audio/wav", ".mp3": "audio/mp3", ".m4a": "audio/aac", ".webm": "audio/webm"}[c.suffix]
            hyp = await transcribe(c.read_bytes(), mime, lang_dir.name)
            if hyp is not None:
                scores.append(wer(ref, hyp))
        rows.append((lang_dir.name, "gemini", len(clips), round(100 * sum(scores) / len(scores), 1) if scores else None))
    text = ["# ASR word error rate", "", "| language | engine | clips | WER % |", "|---|---|---|---|"]
    text += [f"| {a} | {b} | {c} | {'—' if d is None else d} |" for a, b, c, d in rows] or ["| — | — | 0 | — |"]
    if not rows:
        text += ["", "No clips found. Open http://localhost:3000/record and read the 20 sentences per language."]
    (REPORTS / "asr.md").write_text("\n".join(text) + "\n")
    print("\n".join(text))


if __name__ == "__main__":
    asyncio.run(main())
