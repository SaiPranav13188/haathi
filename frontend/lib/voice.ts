"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toWav16k } from "./audio";
import type { Lang } from "./types";

const LOCALE: Record<Lang, string> = { en: "en-IN", hi: "hi-IN", te: "te-IN" };

export type VoiceError = "insecure" | "unsupported" | "denied" | "no-speech" | "failed" | "language";
export type VoicePhase = "idle" | "listening" | "transcribing";

type Rec = {
  lang: string; interimResults: boolean; continuous: boolean; maxAlternatives: number;
  start: () => void; stop: () => void; abort: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null; onend: (() => void) | null;
};

function getRecognizer(): (new () => Rec) | null {
  const w = window as unknown as { SpeechRecognition?: new () => Rec; webkitSpeechRecognition?: new () => Rec };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}


const WORKLET = `class Tap extends AudioWorkletProcessor {
  process(inputs) { const ch = inputs[0] && inputs[0][0]; if (ch) this.port.postMessage(ch.slice(0)); return true; }
}
registerProcessor("haathi-tap", Tap);`;

function liveSocketUrl(): string {
  const env = process.env.NEXT_PUBLIC_BACKEND_WS;
  if (env) return `${env.replace(/\/$/, "")}/api/asr/live`;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.hostname}:8000/api/asr/live`;
}

/** Float32 audio at any rate -> 16 kHz little-endian PCM16 */
function toPcm16(input: Float32Array, rate: number): ArrayBuffer {
  const ratio = rate / 16000;
  const n = Math.floor(input.length / ratio);
  const out = new DataView(new ArrayBuffer(n * 2));
  for (let i = 0; i < n; i++) {
    const v = Math.max(-1, Math.min(1, input[Math.floor(i * ratio)]));
    out.setInt16(i * 2, v * 0x7fff, true);
  }
  return out.buffer;
}

let serverAsr: Promise<boolean> | null = null;
/** Server speech-to-text (Gemini) is used whenever the backend has an LLM; it handles Telugu in every browser. */
function hasServerAsr(): Promise<boolean> {
  serverAsr ??= fetch("/api/meta").then((r) => r.json()).then((m) => !!m?.engine?.llm).catch(() => false);
  return serverAsr;
}

const SILENCE_STOP_MS = 1600;   // stop this long after the person stops talking
const MAX_MS = 15000;           // hard limit per question
const SPEECH_LEVEL = 0.08;      // RMS level (0–1) counted as speech
const LIVE_IDLE_MS = 4000;      // live dictation stops after this long without new words
const STREAM_SILENCE_MS = 3500; // streaming dictation stops this long after the person stops talking
const STREAM_MAX_MS = 60000;

/**
 * Voice dictation into the text box. Nothing is ever sent automatically: the person reviews the words and taps Send.
 *  0. Streaming path (default with Gemini): mic audio is streamed in 100 ms PCM chunks to /api/asr/live (Gemini Live)
 *     and the growing transcript fills the box word by word, in every browser, for Telugu, Hindi and English.
 *  1. Live path (Chrome, Edge, Android Chrome): the Web Speech API streams words while you speak; onText fires on
 *     every update so the box fills in live. Stops when you tap the ear again or after a few seconds of silence.
 *     The mic is not opened a second time (a parallel stream can starve the recogniser on macOS).
 *  2. Recording path (no live recogniser, or it can't do this language, e.g. Telugu in Safari): record, stop on
 *     silence, transcribe with Gemini via /api/asr, then put the whole sentence in the box.
 */
export function useVoiceInput(lang: Lang, onText: (text: string, final: boolean) => void) {
  const [phase, setPhase] = useState<VoicePhase>("idle");
  const [caption, setCaption] = useState("");
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<VoiceError | null>(null);
  const [errorTick, setErrorTick] = useState(0);
  const rec = useRef<Rec | null>(null);
  const media = useRef<{ stream: MediaStream; ctx: AudioContext; raf: number; recorder: MediaRecorder; chunks: Blob[]; heard: boolean } | null>(null);
  const preferRecording = useRef(false); // set when live recognition can't serve this language/browser
  const onTextRef = useRef(onText);
  onTextRef.current = onText;

  const fail = useCallback((e: VoiceError) => { setError(e); setErrorTick((n) => n + 1); setPhase("idle"); setLevel(0); }, []);

  const cleanup = useCallback(() => {
    const m = media.current;
    if (!m) return;
    cancelAnimationFrame(m.raf);
    m.stream.getTracks().forEach((t) => t.stop());
    m.ctx.close().catch(() => {});
    media.current = null;
    setLevel(0);
  }, []);

  const transcribe = useCallback(async (blob: Blob, heard: boolean) => {
    if (!heard) { fail("no-speech"); return; }
    setPhase("transcribing");
    try {
      const wav = await toWav16k(blob);
      const fd = new FormData();
      fd.append("audio", wav, "voice.wav");
      fd.append("lang", lang);
      const r = await fetch("/api/asr", { method: "POST", body: fd });
      if (!r.ok) throw new Error(String(r.status));
      const t = (((await r.json()) as { text: string }).text || "").trim();
      setPhase("idle");
      if (!t) { fail("no-speech"); return; }
      setCaption(t);
      onTextRef.current(t, true);
    } catch {
      fail("failed");
    }
  }, [lang, fail]);

  const startRecording = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    const ctx = new AudioContext();
    const an = ctx.createAnalyser();
    an.fftSize = 1024;
    ctx.createMediaStreamSource(stream).connect(an);
    const recorder = new MediaRecorder(stream);
    const m = { stream, ctx, raf: 0, recorder, chunks: [] as Blob[], heard: false };
    media.current = m;
    const buf = new Uint8Array(an.fftSize);
    const t0 = performance.now();
    let lastVoice = t0;
    recorder.ondataavailable = (e) => { if (e.data.size) m.chunks.push(e.data); };
    recorder.onstop = () => {
      const blob = new Blob(m.chunks, { type: recorder.mimeType || "audio/webm" });
      const heard = m.heard;
      cleanup();
      transcribe(blob, heard);
    };
    const tick = () => {
      an.getByteTimeDomainData(buf);
      let sum = 0;
      for (const v of buf) sum += ((v - 128) / 128) ** 2;
      const lv = Math.min(1, Math.sqrt(sum / buf.length) * 4);
      setLevel(lv);
      const now = performance.now();
      if (lv > SPEECH_LEVEL) { m.heard = true; lastVoice = now; }
      if (((m.heard && now - lastVoice > SILENCE_STOP_MS) || now - t0 > MAX_MS) && recorder.state === "recording") { recorder.stop(); return; }
      m.raf = requestAnimationFrame(tick);
    };
    recorder.start(250);
    setPhase("listening");
    m.raf = requestAnimationFrame(tick);
  }, [cleanup, transcribe]);


  const stream = useRef<{ ws: WebSocket; ctx: AudioContext; mic: MediaStream; done: boolean } | null>(null);

  /** Gemini Live: send 100 ms PCM chunks over a WebSocket, receive the growing transcript. */
  const startStreaming = useCallback(async (): Promise<boolean> => {
    const ws = new WebSocket(liveSocketUrl());
    ws.binaryType = "arraybuffer";
    const ready = await new Promise<boolean>((res) => {
      const t = setTimeout(() => res(false), 8000);
      ws.onmessage = (e) => { try { if (JSON.parse(e.data).type === "ready") { clearTimeout(t); res(true); } else { clearTimeout(t); res(false); } } catch { res(false); } };
      ws.onerror = () => { clearTimeout(t); res(false); };
    });
    if (!ready) { try { ws.close(); } catch { /* */ } return false; }
    const mic = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    const ctx = new AudioContext();
    await ctx.audioWorklet.addModule(URL.createObjectURL(new Blob([WORKLET], { type: "text/javascript" })));
    const node = new AudioWorkletNode(ctx, "haathi-tap");
    ctx.createMediaStreamSource(mic).connect(node);
    const st = { ws, ctx, mic, done: false };
    stream.current = st;
    const t0 = performance.now();
    let lastVoice = t0, heard = false, pending: Float32Array[] = [], pendingLen = 0, latest = "";
    const chunk = Math.round(ctx.sampleRate / 10); // 100 ms
    const finish = () => {
      if (st.done) return;
      st.done = true;
      mic.getTracks().forEach((t) => t.stop());
      ctx.close().catch(() => {});
      setLevel(0);
      if (ws.readyState === WebSocket.OPEN) ws.send("end");
      setPhase("transcribing"); // a moment for the last words
    };
    node.port.onmessage = (e: MessageEvent<Float32Array>) => {
      if (st.done) return;
      const f = e.data;
      let sum = 0;
      for (let i = 0; i < f.length; i++) sum += f[i] * f[i];
      const lv = Math.min(1, Math.sqrt(sum / f.length) * 4);
      setLevel(lv);
      const now = performance.now();
      if (lv > SPEECH_LEVEL) { heard = true; lastVoice = now; }
      pending.push(f); pendingLen += f.length;
      if (pendingLen >= chunk) {
        const all = new Float32Array(pendingLen);
        let o = 0; for (const p of pending) { all.set(p, o); o += p.length; }
        pending = []; pendingLen = 0;
        if (ws.readyState === WebSocket.OPEN) ws.send(toPcm16(all, ctx.sampleRate));
      }
      if ((heard && now - lastVoice > STREAM_SILENCE_MS) || now - t0 > STREAM_MAX_MS) finish();
    };
    ws.onmessage = (e) => {
      const d = JSON.parse(e.data) as { type: string; text?: string };
      if (d.type === "partial" && d.text) { latest = d.text; setCaption(latest); onTextRef.current(latest, false); }
      if (d.type === "final" || d.type === "error") {
        finish();
        stream.current = null;
        setPhase("idle");
        const txt = (d.text || latest).trim();
        if (txt) onTextRef.current(txt, true);
        else if (d.type === "error") fail("failed");
        else fail("no-speech");
        try { ws.close(); } catch { /* */ }
      }
    };
    ws.onclose = () => { if (stream.current === st) { finish(); stream.current = null; setPhase("idle"); if (latest) onTextRef.current(latest, true); } };
    setPhase("listening");
    return true;
  }, [fail]);

  const startLive = useCallback((R: new () => Rec) => {
    let finals = "", latest = "", errored = false, gotWords = false;
    let idle: ReturnType<typeof setTimeout> | null = null;
    const r = new R();
    r.lang = LOCALE[lang]; r.interimResults = true; r.continuous = true; r.maxAlternatives = 1;
    const armIdle = () => { if (idle) clearTimeout(idle); idle = setTimeout(() => r.stop(), LIVE_IDLE_MS); };
    r.onresult = (e) => {
      let fin = "", interim = "";
      for (let i = 0; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) fin += res[0].transcript; else interim += res[0].transcript;
      }
      finals = fin;
      latest = (fin + " " + interim).replace(/\s+/g, " ").trim();
      if (latest) gotWords = true;
      setCaption(latest);
      onTextRef.current(latest, false); // live: words appear in the box as they are recognised
      setLevel(0.45 + Math.random() * 0.45);
      armIdle();
    };
    r.onerror = (e) => {
      errored = true;
      if (e.error === "not-allowed") { fail("denied"); return; }
      if (e.error === "no-speech") { fail("no-speech"); return; }
      if (e.error === "aborted") return;
      // language not available / dictation service off / offline: switch to recording + Gemini for this session
      if (["language-not-supported", "service-not-allowed", "network", "audio-capture"].includes(e.error)) {
        preferRecording.current = true;
        errored = false;
        rec.current = null;
        hasServerAsr().then((ok) => (ok ? startRecording().catch(() => fail("failed")) : fail(e.error === "language-not-supported" ? "language" : "failed")));
        return;
      }
      fail("failed");
    };
    r.onend = () => {
      if (idle) clearTimeout(idle);
      if (rec.current !== r) return; // replaced by the recording fallback
      rec.current = null;
      setLevel(0);
      setPhase("idle");
      const txt = (finals || latest).trim();
      if (txt) onTextRef.current(txt, true);
      else if (!errored && !gotWords) fail("no-speech");
    };
    rec.current = r;
    setPhase("listening");
    armIdle();
    r.start();
  }, [lang, fail, startRecording]);

  const start = useCallback(async () => {
    setError(null); setCaption("");
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) { fail("insecure"); return; }
    try {
      const server = await hasServerAsr();
      if (server && !preferRecording.current && typeof AudioWorkletNode !== "undefined") {
        if (await startStreaming()) return;          // word-by-word in every browser
        // live service busy/unavailable right now: use recording mode for this attempt only
      }
      const R = getRecognizer();
      if (R && !server) { startLive(R); return; }   // no Gemini key: the browser's own live recogniser
      if (server && typeof MediaRecorder !== "undefined") { await startRecording(); return; }
      if (R) { startLive(R); return; }
      fail("unsupported");
    } catch (e) {
      cleanup();
      fail((e as Error)?.name === "NotAllowedError" ? "denied" : "failed");
    }
  }, [fail, startLive, startRecording, startStreaming, cleanup]);

  const stop = useCallback(() => {
    const st = stream.current;
    if (st && !st.done) {
      st.done = true;
      st.mic.getTracks().forEach((t) => t.stop());
      st.ctx.close().catch(() => {});
      setLevel(0);
      if (st.ws.readyState === WebSocket.OPEN) st.ws.send("end");
      setPhase("transcribing");
      return;
    }
    if (rec.current) { rec.current.stop(); return; }
    const m = media.current;
    if (m && m.recorder.state === "recording") { m.heard = true; m.recorder.stop(); } // tapping stop means "I'm done"
  }, []);

  // switching language resets the choice so live recognition is tried again
  useEffect(() => { preferRecording.current = false; }, [lang]);
  useEffect(() => () => {
    rec.current?.abort(); cleanup();
    const st = stream.current; if (st) { st.mic.getTracks().forEach((t) => t.stop()); st.ctx.close().catch(() => {}); try { st.ws.close(); } catch { /* */ } }
  }, [cleanup]);
  return { phase, listening: phase === "listening", transcribing: phase === "transcribing", caption, level, error, errorTick, start, stop };
}

/** Read aloud with the device's speech synthesis voice for the language. */
export function useSpeaker() {
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const speak = useCallback((id: string, text: string, lang: Lang) => {
    if (!("speechSynthesis" in window)) return false;
    window.speechSynthesis.cancel();
    if (speakingId === id) { setSpeakingId(null); return true; }
    const u = new SpeechSynthesisUtterance(text.replace(/\[\d+\]/g, "").replace(/[•✅❌🦎🦋]/gu, ""));
    u.lang = LOCALE[lang];
    const voice = window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith(lang));
    if (voice) u.voice = voice;
    u.rate = 0.95;
    u.onend = () => setSpeakingId(null);
    u.onerror = () => setSpeakingId(null);
    setSpeakingId(id);
    window.speechSynthesis.speak(u);
    return true;
  }, [speakingId]);
  useEffect(() => () => { if ("speechSynthesis" in window) window.speechSynthesis.cancel(); }, []);
  return { speak, speakingId };
}
