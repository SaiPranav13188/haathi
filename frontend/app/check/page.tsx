"use client";

import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { RotateCcw, Undo2 } from "lucide-react";
import { useApp } from "@/lib/app-context";
import { postJSON, profileValues } from "@/lib/api";
import type { Citation, Question, SchemeCard } from "@/lib/types";
import { CATEGORIES } from "@/i18n/strings";
import Gajju from "@/components/Gajju";
import { Peacock } from "@/components/animals";
import { SchemeCardView } from "@/components/SchemeParts";
import { Button } from "@/components/ui";
import { featherFan, pageIn, spring } from "@/animations/motion";

interface NextResp {
  question: Question | null; gain: number | null; ranking: { field: string; gain: number }[]; done: boolean;
  counts: { eligible: number; maybe: number; not_eligible: number }; cards: SchemeCard[]; citations: Citation[];
}

function Counter({ n, label, tone }: { n: number; label: string; tone: string }) {
  return (
    <div className={clsx("flex-1 rounded-2xl px-3 py-2 text-center", tone)}>
      <motion.div key={n} initial={{ scale: 1.4, opacity: 0.4 }} animate={{ scale: 1, opacity: 1 }} transition={spring} className="text-2xl font-extrabold tabular-nums">{n}</motion.div>
      <div className="text-[.75rem] font-semibold leading-tight">{label}</div>
    </div>
  );
}

/** Progress trail: one elephant footprint per answered question. */
function Footprints({ steps, onJump }: { steps: { field: string; label: string; answer: string }[]; onJump: (i: number) => void }) {
  return (
    <ol className="no-scrollbar flex gap-2 overflow-x-auto pb-1" aria-label="Answered questions">
      {steps.map((s, i) => (
        <motion.li key={s.field} initial={{ opacity: 0, scale: 0.5, y: 8 }} animate={{ opacity: 1, scale: 1, y: 0 }} transition={{ ...spring, delay: 0.05 }}>
          <button onClick={() => onJump(i)} className="flex h-10 shrink-0 items-center gap-1.5 rounded-full border border-line bg-surface pl-1.5 pr-3 text-sm" title={s.label}>
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden className={i % 2 ? "rotate-12" : "-rotate-12"}>
              <ellipse cx="12" cy="14" rx="7" ry="8" fill="var(--elephant-dark)" />
              {[6, 10, 14, 18].map((x) => <circle key={x} cx={x} cy="5.5" r="2" fill="var(--elephant-dark)" />)}
            </svg>
            <span className="max-w-28 truncate font-semibold">{s.answer}</span>
          </button>
        </motion.li>
      ))}
    </ol>
  );
}

export default function CheckPage() {
  const { t, lang, profile, setProfile, setMascot, toggleSave, isSaved, toast, motionOK } = useApp();
  const [phase, setPhase] = useState<"intro" | "asking" | "done">("intro");
  const [cats, setCats] = useState<string[]>([]);
  const [asked, setAsked] = useState<string[]>([]);
  const [skipped, setSkipped] = useState<string[]>([]);
  const [resp, setResp] = useState<NextResp | null>(null);
  const [loading, setLoading] = useState(false);
  const [typed, setTyped] = useState("");
  const [err, setErr] = useState(false);

  const fetchNext = useCallback(async (prof = profile, a = asked, s = skipped) => {
    setLoading(true); setErr(false);
    try {
      const r = await postJSON<NextResp>("/api/eligibility/next", { profile: profileValues(prof), lang, categories: cats, asked: a, skipped: s, max_questions: 14 });
      setResp(r);
      if (r.done) {
        setPhase("done");
        setMascot(r.counts.eligible ? "found" : "not_eligible", 2600);
      } else setMascot("asking");
    } catch { setErr(true); setMascot("error"); }
    finally { setLoading(false); }
  }, [profile, asked, skipped, lang, cats, setMascot]);

  useEffect(() => { if (phase !== "intro") fetchNext(); }, [lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const answer = (q: Question, value: unknown, label: string) => {
    const next = { ...profile, [q.field]: { value, source_text: label, method: "answer" } };
    const a = [...asked, q.field];
    setProfile(next); setAsked(a); setTyped("");
    setMascot("nod", 700);
    fetchNext(next, a);
  };
  const undo = () => {
    const last = asked[asked.length - 1];
    if (!last) return;
    const next = { ...profile };
    delete next[last];
    const a = asked.slice(0, -1);
    setProfile(next); setAsked(a); setPhase("asking");
    fetchNext(next, a);
  };
  const jump = (i: number) => {
    const drop = asked.slice(i);
    const next = { ...profile };
    drop.forEach((f) => delete next[f]);
    const a = asked.slice(0, i);
    setProfile(next); setAsked(a); setPhase("asking");
    fetchNext(next, a);
  };
  const restart = () => {
    const next = { ...profile };
    asked.forEach((f) => delete next[f]);
    setProfile(next); setAsked([]); setSkipped([]); setResp(null); setPhase("intro");
  };

  const steps = useMemo(() => asked.filter((f) => profile[f]).map((f) => ({ field: f, label: f, answer: String(profile[f].source_text || profile[f].value) })), [asked, profile]);
  const q = resp?.question;
  const eligible = resp?.cards.filter((c) => c.status === "eligible") ?? [];
  const others = resp?.cards.filter((c) => c.status !== "eligible") ?? [];

  return (
    <motion.div variants={pageIn} initial="hidden" animate="show" className="mx-auto max-w-3xl px-4 pb-10 pt-4">
      <div className="flex items-center gap-3">
        <Gajju state={phase === "done" ? (eligible.length ? "found" : "not_eligible") : loading ? "thinking" : phase === "asking" ? "asking" : "idle"} size={84} />
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">{t("checkTitle")}</h1>
          <p className="text-ink-2">{t("checkIntro")}</p>
        </div>
      </div>

      {phase === "intro" && (
        <motion.section variants={pageIn} initial="hidden" animate="show" className="mt-6">
          <h2 className="mb-3 font-bold">{t("whatFor")}</h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <motion.button whileTap={{ scale: 0.96 }} onClick={() => setCats([])} aria-pressed={cats.length === 0}
              className={clsx("flex min-h-16 items-center gap-2 rounded-2xl border-2 px-3 font-semibold", cats.length === 0 ? "border-peacock bg-peacock-soft" : "border-line bg-surface")}>
              <span className="text-2xl">✨</span>{t("everything")}
            </motion.button>
            {CATEGORIES.map((c) => {
              const on = cats.includes(c.key);
              return (
                <motion.button key={c.key} whileTap={{ scale: 0.96 }} aria-pressed={on}
                  onClick={() => setCats(on ? cats.filter((x) => x !== c.key) : [...cats, c.key])}
                  className={clsx("flex min-h-16 items-center gap-2 rounded-2xl border-2 px-3 text-left font-semibold", on ? "border-peacock bg-peacock-soft" : "border-line bg-surface")}>
                  <span className="text-2xl" aria-hidden>{c.icon}</span>{c.label[lang]}
                </motion.button>
              );
            })}
          </div>
          {Object.keys(profile).length > 0 && (
            <p className="mt-4 rounded-2xl bg-surface-2 px-3 py-2 text-sm text-ink-2">💾 {t("yourProfile")}: {Object.values(profile).map((f) => String(f.source_text || f.value)).slice(0, 6).join(" · ")}</p>
          )}
          <Button size="lg" className="mt-6 w-full" onClick={() => { setPhase("asking"); fetchNext(); }}>{t("start")}</Button>
        </motion.section>
      )}

      {phase !== "intro" && resp && (
        <div className="mt-5 flex gap-2" aria-live="polite">
          <Counter n={resp.counts.eligible} label={t("likelyEligible")} tone="bg-leaf-soft text-leaf" />
          <Counter n={resp.counts.maybe} label={t("needInfo")} tone="bg-amber-soft text-[#9a5b00] dark:text-marigold" />
          <Counter n={resp.counts.not_eligible} label={t("notEligible")} tone="bg-coral-soft text-coral" />
        </div>
      )}
      {phase !== "intro" && steps.length > 0 && <div className="mt-3"><Footprints steps={steps} onJump={jump} /></div>}
      {err && <p className="mt-4 rounded-2xl bg-coral-soft p-3 text-coral">{t("errorBody")} <button className="font-bold underline" onClick={() => fetchNext()}>{t("retry")}</button></p>}

      <AnimatePresence mode="wait">
        {phase === "asking" && q && (
          <motion.section key={q.field} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }} transition={spring}
            className="mt-5 rounded-3xl border border-line bg-surface p-5 shadow-card">
            <p className="text-sm font-bold uppercase tracking-wider text-peacock">{t("question", { n: asked.length + 1 })}</p>
            <h2 className="mt-1 text-[1.35rem] font-bold leading-snug">{q.question}</h2>
            {q.help && <p className="mt-1 text-ink-3">{q.help}</p>}
            <div className={clsx("mt-4 grid gap-2", (q.kind === "number" ? q.buckets : q.options).length > 3 ? "sm:grid-cols-2" : "")}>
              {(q.kind === "number" ? q.buckets : q.options).map((o) => (
                <motion.button key={String(o.value)} whileTap={{ scale: 0.97 }} disabled={loading} onClick={() => answer(q, o.value, o.label)}
                  className="flex min-h-14 items-center justify-between rounded-2xl border border-line bg-surface-2 px-4 text-left text-[1.02rem] font-semibold hover:border-peacock hover:bg-peacock-soft">
                  {o.label}<span aria-hidden className="text-ink-3">→</span>
                </motion.button>
              ))}
            </div>
            {q.kind === "number" && (
              <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); const v = Number(typed); if (typed && Number.isFinite(v)) answer(q, v, `${v.toLocaleString("en-IN")}${q.unit ? " " + q.unit : ""}`); }}>
                <input inputMode="decimal" value={typed} onChange={(e) => setTyped(e.target.value.replace(/[^\d.]/g, ""))} aria-label={q.label}
                  placeholder={`${t("enterNumber")}${q.unit ? ` (${q.unit})` : ""}`} className="h-14 min-w-0 flex-1 rounded-2xl border border-line bg-surface px-4 text-lg outline-none focus:border-peacock" />
                <Button type="submit" size="lg">{t("ok")}</Button>
              </form>
            )}
            <div className="mt-4 flex items-center justify-between gap-2 text-sm">
              <span className="text-ink-3">💡 {t("whyThis")}</span>
              <div className="flex gap-1">
                {asked.length > 0 && <Button size="sm" variant="ghost" onClick={undo}><Undo2 size={16} />{t("undo")}</Button>}
                <Button size="sm" variant="ghost" onClick={() => { const s = [...skipped, q.field]; setSkipped(s); fetchNext(profile, asked, s); }}>{t("skipQuestion")}</Button>
              </div>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {phase === "asking" && resp && eligible.length > 0 && (
        <div className="mt-6">
          <h2 className="mb-2 font-bold text-ink-2">{t("likelyEligible")} · {eligible.length}</h2>
          <div className="flex flex-wrap gap-2">{eligible.map((c) => (
            <motion.span key={c.scheme_id} layout initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="rounded-full bg-leaf-soft px-3 py-1.5 text-sm font-semibold text-leaf">✓ {c.name}</motion.span>
          ))}</div>
        </div>
      )}

      {phase === "done" && resp && (
        <motion.section variants={pageIn} initial="hidden" animate="show" className="mt-6">
          <div className="relative flex flex-col items-center text-center">
            {motionOK && eligible.length > 0 && <Peacock size={190} />}
            <h2 className="mt-2 text-2xl font-extrabold">{t("allDone")}</h2>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {eligible.length > 0 && (
              <Button variant="marigold" onClick={() => { eligible.forEach((c) => !isSaved(c.scheme_id) && toggleSave(c)); setMascot("celebrate", 1500); toast(t("toastChecklist"), "ok", "🎉"); }}>
                🐿️ {t("saveChecklist")}
              </Button>
            )}
            <Button variant="secondary" onClick={undo}><Undo2 size={16} />{t("undo")}</Button>
            <Button variant="secondary" onClick={restart}><RotateCcw size={16} />{t("startOver")}</Button>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {[...eligible, ...others].map((c, i) => (
              <motion.div key={c.scheme_id} variants={featherFan(i, Math.min(eligible.length || 1, 5))} initial="hidden" animate="show">
                <SchemeCardView card={c} citations={resp.citations} msgKey="check" />
              </motion.div>
            ))}
          </div>
          <p className="mt-4 text-sm text-ink-3">⚠️ {t("disclaimer")}</p>
        </motion.section>
      )}
    </motion.div>
  );
}
