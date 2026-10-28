"use client";

/**
 * Speech-test recorder (Prompt 8 / eval/asr_compare.py). Shows a sentence, records you reading it, converts the
 * recording to 16 kHz mono WAV in the browser and saves it as eval/asr_clips/<lang>/clipNN.wav + .txt.
 * Works on http://localhost (microphones need https elsewhere).
 */
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { Check, ChevronLeft, ChevronRight, Play, RotateCcw, Save } from "lucide-react";
import { ASR_PROMPTS } from "@/i18n/asr_prompts";
import Gajju from "@/components/Gajju";
import MicButton from "@/components/MicButton";
import { Button, Segmented } from "@/components/ui";
import { useApp } from "@/lib/app-context";
import { getJSON } from "@/lib/api";
import { toWav16k } from "@/lib/audio";

type L = "te" | "hi" | "en";
const LANG_LABEL: Record<L, string> = { te: "తెలుగు", hi: "हिंदी", en: "English" };

export default function RecordPage() {
  const { toast, setMascot } = useApp();
  const [lang, setLang] = useState<L>("te");
  const [idx, setIdx] = useState(0);
  const [done, setDone] = useState<Record<L, number[]>>({ te: [], hi: [], en: [] });
  const [recording, setRecording] = useState(false);
  const [level, setLevel] = useState(0);
  const [take, setTake] = useState<{ blob: Blob; url: string; secs: number } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const media = useRef<{ stream: MediaStream; rec: MediaRecorder; chunks: Blob[]; ctx: AudioContext; raf: number; t0: number } | null>(null);
  const prompts = ASR_PROMPTS[lang];

  const refresh = useCallback(() => getJSON<Record<L, number[]>>("/api/asr-clips").then(setDone).catch(() => setError("backend")), []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { setTake(null); }, [lang, idx]);

  const start = async () => {
    setError(null); setTake(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, noiseSuppression: false, echoCancellation: false } });
      const ctx = new AudioContext();
      const an = ctx.createAnalyser(); an.fftSize = 512;
      ctx.createMediaStreamSource(stream).connect(an);
      const data = new Uint8Array(an.fftSize);
      const rec = new MediaRecorder(stream);
      const m = { stream, rec, chunks: [] as Blob[], ctx, raf: 0, t0: performance.now() };
      const tick = () => {
        an.getByteTimeDomainData(data);
        let sum = 0; for (const v of data) sum += ((v - 128) / 128) ** 2;
        setLevel(Math.min(1, Math.sqrt(sum / data.length) * 4));
        m.raf = requestAnimationFrame(tick);
      };
      rec.ondataavailable = (e) => m.chunks.push(e.data);
      rec.onstop = async () => {
        cancelAnimationFrame(m.raf); stream.getTracks().forEach((t) => t.stop()); ctx.close();
        const secs = (performance.now() - m.t0) / 1000;
        const wav = await toWav16k(new Blob(m.chunks, { type: rec.mimeType }));
        setTake({ blob: wav, url: URL.createObjectURL(wav), secs });
        setLevel(0);
      };
      media.current = m;
      rec.start(); tick();
      setRecording(true); setMascot("listening");
    } catch {
      setError("mic");
    }
  };
  const stop = () => { media.current?.rec.stop(); setRecording(false); setMascot("idle"); };

  const saveTake = async () => {
    if (!take) return;
    setSaving(true);
    const fd = new FormData();
    fd.append("lang", lang); fd.append("index", String(idx + 1)); fd.append("text", prompts[idx]);
    fd.append("audio", take.blob, `clip${String(idx + 1).padStart(2, "0")}.wav`);
    try {
      const r = await fetch("/api/asr-clips", { method: "POST", body: fd });
      if (!r.ok) throw new Error(await r.text());
      await refresh();
      setMascot("nod", 700);
      toast(`Saved clip ${idx + 1}`, "ok", "🎙️");
      const next = prompts.findIndex((_, i) => i > idx && !done[lang].includes(i + 1));
      if (next >= 0) setIdx(next);
    } catch { setError("save"); } finally { setSaving(false); }
  };

  const total = done.te.length + done.hi.length + done.en.length;
  const isDone = (i: number) => done[lang].includes(i + 1);

  return (
    <div className="mx-auto max-w-2xl px-4 pb-12 pt-4">
      <div className="flex items-center gap-3">
        <Gajju state={recording ? "listening" : total >= 60 ? "celebrate" : "idle"} size={80} voiceLevel={level} />
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Speech test recorder</h1>
          <p className="text-ink-2">Read each sentence aloud in a normal voice. {total}/60 recorded.</p>
        </div>
      </div>

      <div className="mt-4"><Segmented<L> label="Language" value={lang} onChange={(l) => { setLang(l); setIdx(0); }}
        options={(["te", "hi", "en"] as L[]).map((l) => ({ value: l, label: `${LANG_LABEL[l]} ${done[l].length}/20` }))} /></div>

      <div className="mt-3 h-2 overflow-hidden rounded-full bg-ink/[.07]">
        <motion.div className="h-full rounded-full bg-leaf" animate={{ width: `${(done[lang].length / 20) * 100}%` }} />
      </div>

      <section className="mt-5 rounded-3xl border border-line bg-surface p-5 shadow-card">
        <div className="flex items-center justify-between text-sm font-semibold text-ink-3">
          <button onClick={() => setIdx(Math.max(0, idx - 1))} className="grid h-11 w-11 place-items-center rounded-full hover:bg-ink/5" aria-label="Previous"><ChevronLeft /></button>
          <span>Sentence {idx + 1} of 20 {isDone(idx) && <span className="text-leaf">· recorded ✓</span>}</span>
          <button onClick={() => setIdx(Math.min(19, idx + 1))} className="grid h-11 w-11 place-items-center rounded-full hover:bg-ink/5" aria-label="Next"><ChevronRight /></button>
        </div>
        <AnimatePresence mode="wait">
          <motion.p key={`${lang}-${idx}`} lang={lang} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            className="my-6 text-center text-[1.6rem] font-bold leading-snug">{prompts[idx]}</motion.p>
        </AnimatePresence>
        <div className="flex flex-col items-center gap-3">
          <MicButton listening={recording} level={level} onClick={recording ? stop : start} size={84} />
          <p className="text-sm text-ink-3">{recording ? "Recording… tap to stop" : take ? `Recorded ${take.secs.toFixed(1)} s` : "Tap the ear to record"}</p>
          {take && !recording && (
            <div className="flex flex-wrap justify-center gap-2">
              <Button variant="secondary" onClick={() => new Audio(take.url).play()}><Play size={18} />Listen</Button>
              <Button variant="secondary" onClick={start}><RotateCcw size={18} />Re-record</Button>
              <Button onClick={saveTake} disabled={saving || take.secs < 0.8}><Save size={18} />{saving ? "Saving…" : "Save & next"}</Button>
            </div>
          )}
          {isDone(idx) && !take && !recording && (
            <Button variant="ghost" onClick={() => new Audio(`/api/asr-clips/${lang}/${idx + 1}.wav`).play()}><Play size={18} />Play saved clip</Button>
          )}
        </div>
        {error && (
          <p className="mt-4 rounded-2xl bg-coral-soft p-3 text-sm text-coral">
            {error === "mic" ? "Microphone blocked. Allow microphone access for localhost in your browser, then try again."
              : error === "backend" ? "Can't reach the backend. Is `make dev` running?" : "Couldn't save. Is `make dev` running?"}
          </p>
        )}
      </section>

      <ol className="mt-5 grid gap-1.5">
        {prompts.map((p, i) => (
          <li key={i}>
            <button onClick={() => setIdx(i)} className={clsx("flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-left",
              i === idx ? "bg-peacock-soft" : "hover:bg-surface-2")}>
              <span className={clsx("grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold",
                isDone(i) ? "bg-leaf text-white" : "bg-ink/[.07] text-ink-3")}>{isDone(i) ? <Check size={14} /> : i + 1}</span>
              <span lang={lang} className="text-[.95rem] leading-snug">{p}</span>
            </button>
          </li>
        ))}
      </ol>

      {total >= 60 && (
        <p className="mt-6 rounded-2xl bg-leaf-soft p-4 font-medium text-leaf">
          🎉 All 60 clips recorded. Tell Claude (or run <code>cd backend &amp;&amp; uv run python ../eval/asr_compare.py</code>) to measure the word error rate.
        </p>
      )}
      <p className="mt-6 text-xs text-ink-3">Clips are saved on this computer only, in <code>eval/asr_clips/</code>. Recording is turned off when <code>HAATHI_ENV=production</code>.</p>
    </div>
  );
}
