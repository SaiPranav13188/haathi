"use client";

import { AnimatePresence, motion } from "motion/react";
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { ArrowUp, ExternalLink, RotateCcw, ThumbsDown, ThumbsUp, Volume2, VolumeX } from "lucide-react";
import { useApp } from "@/lib/app-context";
import { postJSON, streamChat } from "@/lib/api";
import type { ChatMessage, Citation, DonePayload, Lang, Question } from "@/lib/types";
import { useSpeaker, useVoiceInput } from "@/lib/voice";
import { gajjuFor, useAnimationEvents, type AnimState } from "@/animations/useAnimationEvents";
import { featherFan, messageIn, shake, spring } from "@/animations/motion";
import { SUGGESTIONS } from "@/i18n/strings";
import Gajju from "./Gajju";
import MicButton from "./MicButton";
import { AntTrail, Bird, Owl, Parrot, Peacock, Tortoise, Tree } from "./animals";
import { CitationRow, SchemeCardView } from "./SchemeParts";
import { SourcePage, useSource } from "./SourceViewer";
import { Button, Pill, useMediaQuery } from "./ui";

const uid = () => Math.random().toString(36).slice(2, 10);

/* ============================================================== text with inline citation markers */
function RichText({ text, citations, streaming, msgKey }: { text: string; citations: Citation[]; streaming?: boolean; msgKey: string }) {
  const { motionOK } = useApp();
  const { open } = useSource();
  const byId = useMemo(() => new Map(citations.map((c) => [c.id, c])), [citations]);
  const lines = text.split("\n");
  let wordIndex = 0;
  return (
    <div className={clsx("space-y-1.5 text-[1.02rem] leading-relaxed", streaming && "caret")}>
      {lines.map((line, li) => (
        <p key={li} className={clsx(/^\d+\.|^•/.test(line.trim()) && "pl-1")}>
          {line.split(/(\[\d+\])/).map((part, pi) => {
            const m = part.match(/^\[(\d+)\]$/);
            if (m) {
              const c = byId.get(Number(m[1]));
              return (
                <button key={pi} onClick={() => c && open(c, `cite-${msgKey}-${c.id}`)} disabled={!c}
                  className="mx-0.5 inline-grid h-5 min-w-5 -translate-y-1 place-items-center rounded-full bg-peacock-soft px-1 align-baseline text-[.7rem] font-bold text-peacock hover:bg-peacock hover:text-white"
                  aria-label={`Source ${m[1]}`}>{m[1]}</button>
              );
            }
            return part.split(/(\s+)/).map((w, wi) => {
              if (!w) return null;
              if (/^\s+$/.test(w)) return <Fragment key={`${pi}-${wi}`}>{w}</Fragment>;
              const idx = wordIndex++;
              return motionOK ? (
                <motion.span key={`${pi}-${wi}-${idx}`} initial={{ opacity: 0, filter: "blur(3px)" }} animate={{ opacity: 1, filter: "blur(0px)" }}
                  transition={{ duration: 0.3 }}>{w}</motion.span>
              ) : <span key={`${pi}-${wi}`}>{w}</span>;
            });
          })}
        </p>
      ))}
    </div>
  );
}

/* ============================================================== stage strip (animals = system steps) */
function StageStrip({ a }: { a: AnimState }) {
  const { t, anim } = useApp();
  const label =
    a.phase === "understand" ? t("stUnderstand") :
    a.phase === "retrieve" ? t("stRetrieve", { n: a.passages }) :
    a.phase === "rerank" ? t("stRerank") :
    a.phase === "retry" ? t("stRetry") :
    a.phase === "eligibility" || a.phase === "ask" ? t("stEligibility") :
    a.phase === "verify" ? t("stVerify") : t("stWriting");
  const verified = Object.values(a.verify).filter((s) => s === "supported").length;
  return (
    <div className="mb-2 rounded-2xl bg-surface-2 px-3 py-2" role="status" aria-live="polite">
      {anim !== "off" && (a.phase === "retrieve" || a.phase === "rerank" || a.phase === "retry" || a.phase === "understand") && (
        <AntTrail count={a.passages || 4} mode={a.phase === "rerank" ? "rerank" : a.phase === "retry" ? "retry" : "carry"} />
      )}
      {anim !== "off" && a.phase === "verify" && (
        <div className="flex items-center gap-2"><Owl size={40} />
          <div className="flex gap-1">{Object.entries(a.verify).slice(0, 10).map(([id, s]) => (
            <motion.span key={id} initial={{ scale: 0 }} animate={{ scale: 1 }}
              className={clsx("grid h-5 w-5 place-items-center rounded-full text-[10px] font-bold text-white", s === "supported" ? "bg-leaf" : s === "unsupported" ? "bg-coral" : "bg-marigold")}>
              {s === "supported" ? "✓" : "?"}</motion.span>
          ))}</div>
        </div>
      )}
      <div className="flex items-center gap-2 text-sm font-medium text-ink-2">
        <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-peacock opacity-60" /><span className="relative inline-flex h-2 w-2 rounded-full bg-peacock" /></span>
        <span>{label}{a.phase === "verify" && verified ? ` · ${verified} ✓` : ""}</span>
      </div>
      <AnimatePresence>
        {a.slow && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="relative mt-1 h-10 overflow-hidden">
            {anim !== "off" && <motion.div className="absolute bottom-0" initial={{ left: "-15%" }} animate={{ left: "100%" }} transition={{ duration: 9, ease: "linear", repeat: Infinity }}><Tortoise size={56} /></motion.div>}
            <p className="absolute right-0 top-0 text-xs font-semibold text-ink-3">🐢 {t("slowNetwork")}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ============================================================== quick-reply question card */
function QuestionCard({ qs, onAnswer, onSkip, disabled }: { qs: Question[]; onAnswer: (answers: { q: Question; value: unknown; label: string }[]) => void; onSkip: () => void; disabled?: boolean }) {
  const { t } = useApp();
  const [answers, setAnswers] = useState<Record<string, { value: unknown; label: string }>>({});
  const [typed, setTyped] = useState<Record<string, string>>({});
  const pick = (q: Question, value: unknown, label: string) => {
    const next = { ...answers, [q.field]: { value, label } };
    setAnswers(next);
    if (qs.every((x) => next[x.field])) onAnswer(qs.map((x) => ({ q: x, ...next[x.field] })));
  };
  return (
    <motion.div variants={messageIn} initial="hidden" animate="show" className="mt-3 space-y-3">
      {qs.map((q, i) => (
        <div key={q.field} className="rounded-2xl border border-peacock/25 bg-peacock-soft/40 p-3">
          <p className="mb-2 font-semibold leading-snug"><span className="mr-1.5 text-peacock">{i + 1}.</span>{q.question}</p>
          {q.help && <p className="-mt-1 mb-2 text-sm text-ink-3">{q.help}</p>}
          <div className="flex flex-wrap gap-2">
            {(q.kind === "number" ? q.buckets : q.options).map((o) => {
              const on = answers[q.field]?.label === o.label;
              return (
                <motion.button key={String(o.value)} whileTap={{ scale: 0.95 }} disabled={disabled} onClick={() => pick(q, o.value, o.label)}
                  className={clsx("min-h-12 rounded-2xl border px-4 font-semibold transition-colors",
                    on ? "border-peacock bg-peacock text-white dark:text-[#06242b]" : "border-line bg-surface hover:border-peacock/50")}>{o.label}</motion.button>
              );
            })}
          </div>
          {q.kind === "number" && (
            <form className="mt-2 flex gap-2" onSubmit={(e) => {
              e.preventDefault();
              const v = Number(typed[q.field]);
              if (!Number.isFinite(v) || typed[q.field] === "") return;
              pick(q, v, `${v.toLocaleString("en-IN")}${q.unit ? " " + q.unit : ""}`);
            }}>
              <input inputMode="decimal" placeholder={t("enterNumber") + (q.unit ? ` (${q.unit})` : "")} value={typed[q.field] ?? ""}
                onChange={(e) => setTyped({ ...typed, [q.field]: e.target.value.replace(/[^\d.]/g, "") })}
                className="h-12 min-w-0 flex-1 rounded-2xl border border-line bg-surface px-3 outline-none focus:border-peacock" aria-label={q.label} />
              <Button type="submit" size="md" variant="secondary">{t("ok")}</Button>
            </form>
          )}
        </div>
      ))}
      <button onClick={onSkip} disabled={disabled} className="text-sm font-semibold text-peacock underline-offset-4 hover:underline">{t("showResultsNow")} →</button>
    </motion.div>
  );
}

/* ============================================================== assistant message */
function AssistantMessage({ m, a, active, onAnswer, onSkip, onRetry, onFeedback, speaker }: {
  m: ChatMessage; a: AnimState; active: boolean; onAnswer: (ans: { q: Question; value: unknown; label: string }[]) => void;
  onSkip: () => void; onRetry: () => void; onFeedback: (m: ChatMessage, r: "up" | "down") => void;
  speaker: ReturnType<typeof useSpeaker>;
}) {
  const { t, lang, motionOK, anim } = useApp();
  const d = m.done;
  // stage animals keep playing their (paced) story even if the text already arrived
  const showStages = active && a.phase !== "done" && a.phase !== "idle" && a.phase !== "error";
  const cards = d?.cards ?? [];
  const revealCards = !!d && (!active || a.phase === "done");
  const [owlNote, setOwlNote] = useState(false);
  const eligibleReveal = d?.kind === "eligible";

  if (m.error) {
    return (
      <motion.div variants={messageIn} initial="hidden" animate="show" className="flex items-center gap-3 rounded-3xl border border-coral/30 bg-coral-soft/60 p-4">
        <Gajju state="error" size={72} />
        <div className="flex-1">
          <p className="font-bold">{t("errorTitle")}</p>
          <p className="text-sm text-ink-2">{t("errorBody")}</p>
          <Button size="sm" className="mt-2" onClick={onRetry}><RotateCcw size={16} />{t("retry")}</Button>
        </div>
      </motion.div>
    );
  }
  return (
    <motion.div variants={messageIn} initial="hidden" animate="show" className="max-w-full">
      {showStages && <StageStrip a={a} />}
      {(m.text || d) && (
        <div className="rounded-3xl rounded-tl-lg border border-line bg-surface px-4 py-3 shadow-card">
          <RichText text={d?.text ?? m.text} citations={d?.citations ?? []} streaming={m.streaming && !d} msgKey={m.id} />
          {d?.abstained && d.official_links?.length > 0 && (
            <div className="mt-3 flex items-start gap-3 rounded-2xl bg-peacock-soft/60 p-3">
              <Gajju state="unsure" size={64} />
              <div className="space-y-1.5">
                <p className="text-sm font-semibold">{t("checkOfficial")}</p>
                {d.official_links.map((l) => (
                  <a key={l.url} href={l.url} target="_blank" rel="noreferrer" className="flex min-h-10 items-center gap-1.5 font-semibold text-peacock underline-offset-4 hover:underline">
                    {l.label} <ExternalLink size={14} /></a>
                ))}
              </div>
            </div>
          )}
          {d && d.profile_updates.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs">
              <span className="font-semibold text-ink-3">{t("yourProfile")}:</span>
              {d.profile_updates.map((f) => <Pill key={f.field} tone="peacock">“{f.source_text}”</Pill>)}
            </div>
          )}
        </div>
      )}

      {/* 🦚 peacock reveal: cards spread out like feathers */}
      {revealCards && cards.length > 0 && (
        <div className="relative mt-3">
          {eligibleReveal && motionOK && anim === "full" && (
            <motion.div className="pointer-events-none absolute -top-8 left-1/2 z-0 -translate-x-1/2" initial={{ opacity: 1 }} animate={{ opacity: 0 }} transition={{ delay: 1.6, duration: 0.6 }}>
              <Peacock size={170} />
            </motion.div>
          )}
          <div className="relative z-10 grid gap-3 md:grid-cols-2">
            {cards.map((c, i) => (
              <motion.div key={c.scheme_id} variants={featherFan(i, Math.min(cards.length, 5))} initial="hidden" animate="show">
                <SchemeCardView card={c} citations={d!.citations} msgKey={m.id} />
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {d && d.questions.length > 0 && revealCards && (
        <div className="mt-3 rounded-3xl border border-line bg-surface px-4 py-3 shadow-card" id={`q-${m.id}`}>
          <QuestionCard qs={d.questions} onAnswer={onAnswer} onSkip={onSkip} disabled={!active} />
        </div>
      )}

      {d && <CitationRow citations={d.citations.slice(0, 12)} verifying={active && a.phase === "verify"} msgKey={m.id} />}

      {d && !m.streaming && (
        <div className="mt-2 flex flex-wrap items-center gap-1 text-ink-3">
          <button onClick={() => speaker.speak(m.id, d.text, d.lang as Lang)} className="flex h-11 items-center gap-1.5 rounded-full px-3 text-sm font-semibold hover:bg-ink/5">
            {speaker.speakingId === m.id ? <VolumeX size={18} /> : <Volume2 size={18} />}{speaker.speakingId === m.id ? t("stopReading") : t("readAloud")}
          </button>
          <button onClick={() => onFeedback(m, "up")} aria-pressed={m.feedback === "up"} aria-label={t("helpful")}
            className={clsx("grid h-11 w-11 place-items-center rounded-full hover:bg-ink/5", m.feedback === "up" && "text-leaf")}><ThumbsUp size={18} /></button>
          <button onClick={() => { onFeedback(m, "down"); setOwlNote(true); }} aria-pressed={m.feedback === "down"} aria-label={t("notHelpful")}
            className={clsx("grid h-11 w-11 place-items-center rounded-full hover:bg-ink/5", m.feedback === "down" && "text-coral")}><ThumbsDown size={18} /></button>
          <AnimatePresence>
            {owlNote && (
              <motion.span initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="flex items-center gap-1 text-sm">
                <Owl size={36} writing /> {t("owlThanks")}
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      )}
      {d?.disclaimer && <p className="mt-1 px-1 text-[.8rem] leading-snug text-ink-3">⚠️ {d.disclaimer}</p>}
      {/* hidden for screen readers so they read answers in the right language */}
      <span className="sr-only" lang={d?.lang ?? lang} />
    </motion.div>
  );
}

/* ============================================================== empty state */
function EmptyState({ onPick }: { onPick: (s: string) => void }) {
  const { t, lang, motionOK } = useApp();
  return (
    <div className="flex flex-col items-center px-2 pb-6 pt-4 text-center">
      <div className="relative h-56 w-72">
        <Tree className="absolute inset-0 h-full w-full" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2"><Gajju state="idle" size={128} /></div>
        <motion.div className="absolute bottom-[112px] left-[148px]" animate={motionOK ? { y: [0, -3, 0] } : {}} transition={{ duration: 2.2, repeat: Infinity }}>
          <Bird size={26} />
        </motion.div>
      </div>
      <h1 className="mt-3 text-2xl font-extrabold tracking-tight">{t("greetingTitle")}</h1>
      <p className="mt-1 max-w-md text-ink-2">{t("greetingBody")}</p>
      <p className="mt-6 text-xs font-bold uppercase tracking-widest text-ink-3">🍃 {t("tryAsking")}</p>
      <div className="mt-2 grid w-full max-w-xl gap-2 sm:grid-cols-2">
        {SUGGESTIONS[lang].map((s, i) => (
          <motion.button key={s} onClick={() => onPick(s)}
            initial={motionOK ? { opacity: 0, y: -40, rotate: i % 2 ? 8 : -8 } : false}
            animate={{ opacity: 1, y: 0, rotate: 0 }} transition={{ type: "spring", stiffness: 90, damping: 11, delay: 0.15 + i * 0.12 }}
            whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}
            className="group flex min-h-14 items-center gap-2 rounded-[22px] rounded-tl-md border border-leaf/25 bg-leaf-soft/60 px-4 py-2.5 text-left font-medium leading-snug text-ink hover:border-leaf/50">
            <span aria-hidden className="text-lg">🍃</span><span>{s}</span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}

/* ============================================================== page */
export default function ChatScreen() {
  const app = useApp();
  const { t, lang, profile, setProfile, messages, setMessages, chatMeta, setChatMeta, setMascot, motionOK, toast } = app;
  const { anim: a, begin, onEvent, fail } = useAnimationEvents(!motionOK);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [shakeKey, setShakeKey] = useState(0);
  const activeId = useRef<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const speaker = useSpeaker();
  const wide = useMediaQuery("(min-width: 1024px)");
  const source = useSource();

  useEffect(() => { source.setDocked(true); return () => source.setDocked(false); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const send = useCallback(async (text: string, opts: { skip?: boolean; profileOverride?: typeof profile; display?: string } = {}) => {
    const msg = text.trim();
    if (!msg || busy) { if (!msg) setShakeKey((k) => k + 1); return; }
    const userMsg: ChatMessage = { id: uid(), role: "user", text: opts.display ?? msg };
    const botId = uid();
    activeId.current = botId;
    setMessages((ms) => [...ms, userMsg, { id: botId, role: "assistant", text: "", streaming: true }]);
    setInput("");
    setBusy(true);
    begin();
    const ctrl = new AbortController();
    abort.current = ctrl;
    const prof = opts.profileOverride ?? profile;
    try {
      await streamChat({ message: msg, lang, profile: prof, pending: chatMeta.pending, asked: chatMeta.asked, focus: chatMeta.focus, skip_questions: opts.skip },
        (e) => {
          onEvent(e);
          if (e.type === "token") setMessages((ms) => ms.map((m) => (m.id === botId ? { ...m, text: m.text + e.text } : m)));
          else if (e.type === "stage" && e.stage === "understand") {
            setMessages((ms) => ms.map((m) => (m.id === userMsg.id ? { ...m, detected: { lang: String(e.lang), romanized: !!e.romanized, code_mixed: !!e.code_mixed } } : m)));
          } else if (e.type === "done") {
            const d = e as DonePayload;
            setMessages((ms) => ms.map((m) => (m.id === botId ? { ...m, text: d.text, done: d, streaming: false, lang: d.lang } : m)));
            if (d.profile_updates.length) {
              setProfile((p) => {
                const n = { ...p };
                for (const f of d.profile_updates) n[f.field] = { value: f.value, source_text: f.source_text, method: f.method };
                return n;
              });
            }
            const qf = d.questions.map((q) => q.field);
            setChatMeta({ pending: qf, asked: [...new Set([...chatMeta.asked, ...qf])], focus: d.focus });
          } else if (e.type === "error") {
            setMessages((ms) => ms.map((m) => (m.id === botId ? { ...m, error: e.message, streaming: false } : m)));
          }
        }, ctrl.signal);
    } catch {
      fail();
      setMessages((ms) => ms.map((m) => (m.id === botId ? { ...m, error: "network", streaming: false } : m)));
    } finally {
      setBusy(false);
    }
  }, [busy, setMessages, begin, profile, lang, chatMeta, onEvent, setProfile, setChatMeta, fail]);

  // Dictation fills the text box (live where the browser supports it); the person reviews and taps Send.
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const voiceBase = useRef("");
  const voice = useVoiceInput(lang, useCallback((txt: string, final: boolean) => {
    const base = voiceBase.current;
    setInput(base ? `${base} ${txt}` : txt);
    if (final) {
      requestAnimationFrame(() => {
        const el = inputRef.current;
        if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); }
      });
    }
  }, []));
  const toggleMic = () => {
    if (voice.listening) { voice.stop(); return; }
    if (voice.transcribing) return;
    voiceBase.current = input.trim();
    voice.start();
  };
  useEffect(() => {
    if (!voice.error) return;
    const key = { unsupported: "micUnsupported", denied: "micDenied", insecure: "micInsecure", "no-speech": "micNoSpeech",
                  failed: "micFailed", language: "micLanguage" }[voice.error] as "micUnsupported";
    toast(t(key), "warn", "🎙️");
  }, [voice.errorTick]); // eslint-disable-line react-hooks/exhaustive-deps

  // Gajju mirrors what the system is doing
  useEffect(() => {
    const s = voice.transcribing ? "thinking" : gajjuFor(a, voice.listening);
    if (a.phase === "done" && (s === "found" || s === "not_eligible" || s === "unsure")) setMascot(s, 2600);
    else setMascot(s);
  }, [a.phase, a.result, voice.listening, voice.transcribing, setMascot]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: motionOK ? "smooth" : "auto", block: "end" }); }, [messages.length, motionOK]);
  useEffect(() => {
    if (a.phase !== "done" || !activeId.current) return;
    const el = document.getElementById(`msg-${activeId.current}`);
    const tm = setTimeout(() => el?.scrollIntoView({ behavior: motionOK ? "smooth" : "auto", block: "start" }), 120);
    return () => clearTimeout(tm);
  }, [a.phase, motionOK]);

  const answerQuestions = (ans: { q: Question; value: unknown; label: string }[]) => {
    const next = { ...profile };
    for (const x of ans) next[x.q.field] = { value: x.value, source_text: x.label, method: "answer" };
    setProfile(next);
    send(ans.map((x) => x.label).join(", "), { profileOverride: next });
  };
  const lastUser = [...messages].reverse().find((m) => m.role === "user");

  const newChat = () => {
    abort.current?.abort();
    setMessages([]);
    setChatMeta({ pending: [], asked: [], focus: [] });
    setMascot("wave", 1500);
  };

  return (
    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(360px,440px)] lg:gap-4 lg:px-4">
      <section className="flex min-h-[calc(100dvh-4rem-76px)] flex-col lg:min-h-[calc(100dvh-4rem)]">
        <div className="flex-1 px-4 pt-3">
          {messages.length === 0 ? <EmptyState onPick={(s) => send(s)} /> : (
            <div className="mx-auto max-w-3xl space-y-4 pb-4">
              <div className="flex justify-end">
                <button onClick={newChat} className="flex h-10 items-center gap-1.5 rounded-full px-3 text-sm font-semibold text-ink-3 hover:bg-ink/5"><RotateCcw size={15} />{t("newChat")}</button>
              </div>
              {messages.map((m) => m.role === "user" ? (
                <motion.div key={m.id} variants={messageIn} initial="hidden" animate="show" className="flex flex-col items-end gap-1">
                  <div className="max-w-[85%] rounded-3xl rounded-tr-lg bg-peacock px-4 py-2.5 text-[1.02rem] text-white shadow-card dark:text-[#06242b]">{m.text}</div>
                  <AnimatePresence>
                    {m.detected && (m.detected.lang !== "en" || m.detected.romanized || m.detected.code_mixed) && (
                      <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} className="flex items-center gap-1 text-xs text-ink-3">
                        <Parrot size={28} talking={false} />
                        {t("heardIn", { lang: t(`langName_${m.detected.lang}` as "langName_en") })}
                        {m.detected.romanized ? ` · ${t("romanized")}` : m.detected.code_mixed ? ` · ${t("codeMixed")}` : ""}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ) : (
                <div key={m.id} id={`msg-${m.id}`} className="flex scroll-mt-20 items-start gap-2">
                  <div className="hidden shrink-0 sm:block"><Gajju state={m.id === activeId.current ? app.mascot : "idle"} size={40} decorative /></div>
                  <div className="min-w-0 flex-1">
                    <AssistantMessage m={m} a={a} active={m.id === activeId.current} speaker={speaker}
                      onAnswer={answerQuestions} onSkip={() => send(t("showResultsNow"), { skip: true })}
                      onRetry={() => lastUser && send(lastUser.text)}
                      onFeedback={(mm, r) => {
                        setMessages((ms) => ms.map((x) => (x.id === mm.id ? { ...x, feedback: r } : x)));
                        if (r === "up") setMascot("hop", 900);
                        postJSON("/api/feedback", { rating: r, message: lastUser?.text ?? "", answer: mm.done?.text ?? "", lang }).catch(() => {});
                        toast(t("toastThanks"), "ok", r === "up" ? "🐘" : "🦉");
                      }} />
                  </div>
                </div>
              ))}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {/* composer */}
        <div className="sticky bottom-[calc(76px+env(safe-area-inset-bottom))] z-20 bg-gradient-to-t from-sand via-sand/95 to-transparent px-3 pb-3 pt-4 lg:bottom-0">
          <AnimatePresence>
            {(voice.listening || voice.transcribing) && (
              <motion.p initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="mx-auto mb-2 max-w-3xl rounded-2xl bg-ink px-4 py-2 text-center text-sand" aria-live="polite">
                {voice.transcribing ? `✍️ ${t("transcribing")}` : `🎙️ ${t("listeningHint")}`}
              </motion.p>
            )}
          </AnimatePresence>
          <motion.form key={shakeKey} animate={shakeKey ? shake : undefined}
            onSubmit={(e) => { e.preventDefault(); if (voice.listening) voice.stop(); send(input); }}
            className="mx-auto flex max-w-3xl items-end gap-2 rounded-[28px] border border-line bg-surface p-1.5 shadow-lift transition-shadow focus-within:border-peacock focus-within:ring-4 focus-within:ring-peacock/15">
            <MicButton listening={voice.listening} level={voice.level} onClick={toggleMic} />
            <label className="sr-only" htmlFor="chat-input">{t("placeholder")}</label>
            <textarea id="chat-input" ref={inputRef} rows={1} value={input} onChange={(e) => setInput(e.target.value)} placeholder={t("placeholder")}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (voice.listening) voice.stop(); send(input); } }}
              className={clsx("max-h-36 min-h-14 flex-1 resize-none bg-transparent px-1 py-[15px] text-[1.02rem] leading-snug outline-none placeholder:text-ink-3 focus-visible:outline-none",
                voice.listening && "text-peacock")} />
            <motion.button type="submit" whileTap={{ scale: 0.9 }} disabled={busy} aria-label={t("send")}
              className={clsx("grid h-14 w-14 shrink-0 place-items-center rounded-full transition-colors",
                input.trim() ? "bg-peacock text-white dark:text-[#06242b]" : "bg-ink/[.07] text-ink-3")}>
              {busy ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" /> : <ArrowUp size={24} strokeWidth={2.6} />}
            </motion.button>
          </motion.form>
          <p className="mx-auto mt-1.5 max-w-3xl text-center text-[.72rem] text-ink-3">🔒 {t("privacyNote")}</p>
        </div>
      </section>

      {/* desktop: source viewer on the right */}
      {wide && (
        <aside className="sticky top-20 hidden h-[calc(100dvh-6rem)] overflow-y-auto rounded-3xl border border-line bg-surface p-4 shadow-card lg:block" aria-label={t("sources")}>
          <AnimatePresence mode="wait">
            {source.current ? (
              <motion.div key={`${source.current.doc}-${source.current.id}`} layoutId={source.layoutId ?? undefined} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={spring}>
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h2 className="text-lg font-bold leading-tight">{source.current.title}</h2>
                  <button onClick={source.close} className="rounded-full px-2 text-sm text-ink-3 hover:bg-ink/5">{t("close")}</button>
                </div>
                <SourcePage citation={source.current} />
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid h-full place-items-center text-center text-ink-3">
                <div><Owl size={90} looking /><p className="mt-2 max-w-60 text-sm">{t("sources")} · {t("seedNotice")}</p></div>
              </motion.div>
            )}
          </AnimatePresence>
        </aside>
      )}
    </div>
  );
}
