"""Live dictation: stream microphone audio to Gemini Live and stream the transcript back as it is recognised.

Browser  ──(binary PCM16 16 kHz chunks, then "end")──▶  /api/asr/live  ──▶  Gemini Live (native-audio model)
Browser  ◀──({"type":"partial"|"final","text": ...})──  input_audio_transcription deltas

Only the *input transcription* is used; the model is told to stay silent and its audio reply is discarded.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from ..config import get_settings

log = logging.getLogger(__name__)
SILENT = ("You are only a microphone for a dictation box. Never answer, never speak, never translate. "
          "The user speaks Telugu, Hindi or English, sometimes mixed.")


async def live_dictation(ws: WebSocket) -> None:
    await ws.accept()
    s = get_settings()
    if not s.gemini_api_key:
        await ws.send_json({"type": "error", "reason": "no-llm"})
        await ws.close()
        return
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=s.gemini_api_key)
    cfg = types.LiveConnectConfig(response_modalities=["AUDIO"], system_instruction=SILENT,
                                  input_audio_transcription=types.AudioTranscriptionConfig())
    text = ""
    ended = asyncio.Event()
    try:
        async with client.aio.live.connect(model=s.gemini_live_model, config=cfg) as session:
            await ws.send_json({"type": "ready"})

            async def pump_mic() -> None:
                try:
                    while True:
                        msg = await ws.receive()
                        if msg.get("type") == "websocket.disconnect":
                            break
                        if msg.get("bytes"):
                            await session.send_realtime_input(audio=types.Blob(data=msg["bytes"], mime_type="audio/pcm;rate=16000"))
                        elif msg.get("text") == "end":
                            await session.send_realtime_input(audio_stream_end=True)
                            break
                finally:
                    ended.set()

            async def pump_words() -> None:
                nonlocal text
                async for m in session.receive():
                    sc = m.server_content
                    piece = sc.input_transcription.text if sc and sc.input_transcription else None
                    if piece:
                        text += piece
                        await ws.send_json({"type": "partial", "text": " ".join(text.split())})
                    if sc and sc.turn_complete and ended.is_set():
                        return

            mic = asyncio.create_task(pump_mic())
            words = asyncio.create_task(pump_words())
            await ended.wait()
            # after the person stops, give the last words a moment to arrive
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(words), timeout=3.0)
            for t in (mic, words):
                t.cancel()
            await ws.send_json({"type": "final", "text": " ".join(text.split())})
    except WebSocketDisconnect:
        return
    except Exception as e:  # quota, network, model unavailable → the browser falls back to recording mode
        log.warning("live dictation failed: %s", str(e)[:200])
        with contextlib.suppress(Exception):
            await ws.send_json({"type": "error", "reason": "live-unavailable", "text": " ".join(text.split())})
    with contextlib.suppress(Exception):
        await ws.close()
