"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { Bookmark, BookmarkCheck, Check, ChevronDown, ExternalLink, HelpCircle, Search, X } from "lucide-react";
import { useApp } from "@/lib/app-context";
import type { Citation, RuleRow, SchemeCard as Card } from "@/lib/types";
import { load, save } from "@/lib/storage";
import { rowIn, spring, stagger, tickIn } from "@/animations/motion";
import { Bee, Butterfly, Chameleon, Owl } from "./animals";
import { CountUp, Pill } from "./ui";
import { useSource } from "./SourceViewer";

export const CAT_ICON: Record<string, string> = {
  farmers: "🌾", students: "🎓", women: "👩", seniors: "🧓", housing: "🏠", health: "🏥", insurance: "🛡️",
  workers: "🧰", pension: "🪙", households: "💡", savings: "🐷",
};

const STATE_NAMES: Record<string, Record<string, string>> = {
  Telangana: { en: "Telangana", hi: "तेलंगाना", te: "తెలంగాణ" },
  "Andhra Pradesh": { en: "Andhra Pradesh", hi: "आंध्र प्रदेश", te: "ఆంధ్రప్రదేశ్" },
};
export function stateLabel(state: string | null, lang: string): string | null {
  return state ? STATE_NAMES[state]?.[lang] ?? state : null;
}

export function StatusPill({ status, label }: { status: Card["status"]; label: string }) {
  const tone = status === "eligible" ? "leaf" : status === "maybe" ? "amber" : "coral";
  const Icon = status === "eligible" ? Check : status === "maybe" ? HelpCircle : X;
  return <Pill tone={tone}><Icon size={14} strokeWidth={3} />{label}</Pill>;
}

/* ---------------------------------------------------------------- citations */
export function CitationChip({ c, msgKey = "" }: { c: Citation; msgKey?: string }) {
  const { t } = useApp();
  const { open } = useSource();
  const status = c.status;
  return (
    <motion.button layoutId={`cite-${msgKey}-${c.id}`} onClick={() => open(c, `cite-${msgKey}-${c.id}`)} whileTap={{ scale: 0.95 }}
      className={clsx("inline-flex h-8 items-center gap-1.5 rounded-full border px-2.5 text-[.8rem] font-semibold transition-colors",
        status === "supported" ? "border-leaf/30 bg-leaf-soft text-leaf" : status === "unsupported" ? "border-coral/30 bg-coral-soft text-coral"
          : status === "pending" ? "border-line bg-surface text-ink-3" : "border-marigold/40 bg-amber-soft text-[#9a5b00] dark:text-marigold")}
      aria-label={`${t("sources")} ${c.id}: ${c.title}, ${t("page", { n: c.page })}. ${status === "supported" ? t("verified") : status}`}>
      <span className="grid h-5 min-w-5 place-items-center rounded-full bg-current/10 px-1 text-[.72rem]"><span className="text-current">{c.id}</span></span>
      <span className="max-w-[9.5rem] truncate">{t("page", { n: c.page })}</span>
      <AnimatePresence mode="wait">
        {status === "pending" ? (
          <motion.span key="p" exit={{ scale: 0 }}><Search size={13} className="animate-pulse" /></motion.span>
        ) : status === "supported" ? (
          <motion.span key="s" initial={{ scale: 0 }} animate={{ scale: [0, 1.4, 1] }}><Check size={14} strokeWidth={3} /></motion.span>
        ) : status === "unsupported" ? <X size={13} /> : <HelpCircle size={13} />}
      </AnimatePresence>
    </motion.button>
  );
}

export function CitationRow({ citations, verifying, msgKey }: { citations: Citation[]; verifying?: boolean; msgKey: string }) {
  const { t, anim } = useApp();
  if (!citations.length) return null;
  return (
    <div className="mt-3">
      <div className="mb-1.5 flex items-center gap-2 text-sm font-semibold text-ink-2">
        {verifying && anim !== "off" ? <Owl size={34} /> : <span aria-hidden>🦉</span>}
        <span>{verifying ? t("stVerify") : t("sources")}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">{citations.map((c) => <CitationChip key={c.id} c={c} msgKey={msgKey} />)}</div>
    </div>
  );
}

/* ---------------------------------------------------------------- rule checklist */
export function RuleChecklist({ rules, citations, onRowShown, msgKey = "" }: {
  rules: RuleRow[]; citations?: Citation[]; onRowShown?: (r: RuleRow) => void; msgKey?: string;
}) {
  const { t } = useApp();
  const { open } = useSource();
  const byId = useMemo(() => new Map((citations ?? []).map((c) => [c.id, c])), [citations]);
  return (
    <motion.ul variants={stagger(0.14, 0.1)} initial="hidden" animate="show" className="divide-y divide-line/70">
      {rules.map((r) => {
        const c = byId.get(r.citation);
        return (
          <motion.li key={r.id} variants={rowIn} onAnimationComplete={() => onRowShown?.(r)} className="flex items-start gap-3 py-2.5">
            <motion.span variants={tickIn}
              className={clsx("mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-bold",
                r.result === "pass" ? "bg-leaf text-white" : r.result === "fail" ? "bg-coral text-white" : "bg-marigold-soft text-[#9a5b00] dark:text-marigold")}
              aria-label={r.result === "pass" ? "met" : r.result === "fail" ? "not met" : "unknown"}>
              {r.result === "pass" ? <Check size={16} strokeWidth={3.2} /> : r.result === "fail" ? <X size={16} strokeWidth={3.2} /> : "?"}
            </motion.span>
            <div className="min-w-0 flex-1">
              <p className="font-medium leading-snug">{r.label}</p>
              <p className="text-sm text-ink-3">
                {r.user_value != null ? <>{t("youSaid")}: <b className="font-semibold text-ink-2">{r.user_value}</b></> : t("unknownYet")}
              </p>
              {r.quote && (
                <button onClick={() => c && open(c)} className="mt-1 block text-left text-[.85rem] italic leading-snug text-ink-3 underline decoration-marigold/60 decoration-2 underline-offset-4 hover:text-ink-2">
                  “{r.quote}” <span className="not-italic text-peacock">· {t("page", { n: c?.page ?? "" })}</span>
                </button>
              )}
            </div>
          </motion.li>
        );
      })}
    </motion.ul>
  );
}

/* ---------------------------------------------------------------- 🐝 document checklist */
export function DocumentChecklist({ schemeId, documents }: { schemeId: string; documents: Card["documents"] }) {
  const { t, setMascot, motionOK } = useApp();
  const key = `docs:${schemeId}`;
  const [done, setDone] = useState<string[]>(() => (typeof window === "undefined" ? [] : load<string[]>(key, [])));
  const complete = documents.length > 0 && documents.every((d) => done.includes(d.key));
  const toggle = (k: string) => {
    const next = done.includes(k) ? done.filter((x) => x !== k) : [...done, k];
    setDone(next);
    save(key, next);
    if (documents.every((d) => next.includes(d.key))) setMascot("celebrate", 1400);
  };
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-semibold text-ink-2">{complete ? `🍯 ${t("docsDone")}` : t("docsProgress", { d: done.filter((k) => documents.some((x) => x.key === k)).length, n: documents.length })}</span>
      </div>
      <ul className="grid gap-2 sm:grid-cols-2">
        {documents.map((d) => {
          const on = done.includes(d.key);
          return (
            <li key={d.key} className="relative">
              <button onClick={() => toggle(d.key)} aria-pressed={on}
                className={clsx("relative flex min-h-12 w-full items-center gap-3 overflow-hidden rounded-2xl border px-3 py-2 text-left transition-colors",
                  on ? "border-marigold/50 bg-marigold-soft" : "border-line bg-surface hover:bg-surface-2")}>
                {/* honeycomb fill */}
                <AnimatePresence>
                  {on && motionOK && (
                    <motion.span className="absolute inset-0 -z-0 opacity-30" initial={{ clipPath: "circle(0% at 12% 50%)" }} animate={{ clipPath: "circle(140% at 12% 50%)" }}
                      exit={{ opacity: 0 }} transition={{ duration: 0.55 }}
                      style={{ backgroundImage: "radial-gradient(circle at 10px 10px, #f4c21b 6px, transparent 7px)", backgroundSize: "18px 16px" }} />
                  )}
                </AnimatePresence>
                <span className={clsx("relative grid h-7 w-7 shrink-0 place-items-center text-sm", on ? "text-[#7a4a00]" : "text-ink-3")}
                  style={{ clipPath: "polygon(25% 5%, 75% 5%, 100% 50%, 75% 95%, 25% 95%, 0% 50%)", background: on ? "var(--marigold)" : "var(--sand-deep)" }}>
                  {on && <Check size={15} strokeWidth={3} />}
                </span>
                <span className="relative font-medium">{d.label}</span>
                <AnimatePresence>
                  {on && motionOK && (
                    <motion.span className="absolute right-2 top-1" initial={{ x: 60, y: -20, opacity: 0 }} animate={{ x: [60, 0, -6, 30], y: [-20, 0, 2, -30], opacity: [0, 1, 1, 0] }}
                      transition={{ duration: 1.3 }}><Bee size={20} /></motion.span>
                  )}
                </AnimatePresence>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/* ---------------------------------------------------------------- 🦋 what-if */
export function WhatIfNote({ card }: { card: Card }) {
  const { motionOK } = useApp();
  if (!card.what_if) return null;
  return (
    <div className="relative mt-3 overflow-hidden rounded-2xl border border-dashed border-marigold/60 bg-amber-soft/70 px-3.5 py-3">
      {motionOK && (
        <motion.div className="absolute" initial={{ left: "-10%", top: "70%" }} animate={{ left: ["-10%", "40%", "88%"], top: ["70%", "10%", "18%"] }}
          transition={{ duration: 1.6, ease: "easeInOut" }} aria-hidden><Butterfly size={26} /></motion.div>
      )}
      <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden preserveAspectRatio="none" viewBox="0 0 100 40">
        {motionOK && <motion.path d="M0 30 Q 40 0 92 8" stroke="var(--marigold)" strokeWidth=".6" strokeDasharray="1.5 2" fill="none"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.6 }} />}
      </svg>
      <p className="relative pr-8 text-[.95rem] font-medium leading-snug text-[#7a4a00] dark:text-marigold">🦋 {card.what_if.text}</p>
    </div>
  );
}

/* ---------------------------------------------------------------- freshness */
export function FreshnessBadge({ card }: { card: Card }) {
  const { t } = useApp();
  if (!card.changed_on) return null;
  return (
    <div className="mt-2 flex items-start gap-2 rounded-xl bg-peacock-soft/60 px-2.5 py-2 text-[.85rem] text-ink-2">
      <Chameleon size={34} />
      <span><b className="font-semibold text-ink">{t("ruleChanged", { d: card.changed_on })}</b>{card.change_note ? ` — ${card.change_note}` : ""}</span>
    </div>
  );
}

/* ---------------------------------------------------------------- the card */
export function SchemeCardView({ card, citations, msgKey = "", compact = false }: { card: Card; citations?: Citation[]; msgKey?: string; compact?: boolean }) {
  const { t, isSaved, toggleSave, lang } = useApp();
  const [open, setOpen] = useState(false);
  const saveRef = useRef<HTMLButtonElement>(null);
  const passed = card.rules.filter((r) => r.result === "pass").length;
  const saved = isSaved(card.scheme_id);
  const icon = CAT_ICON[card.categories[0]] ?? "📄";
  const tone = card.status === "eligible" ? "from-leaf-soft" : card.status === "maybe" ? "from-amber-soft" : "from-coral-soft";
  return (
    <motion.article layoutId={`card-${msgKey}-${card.scheme_id}`} layout="position"
      className="overflow-hidden rounded-3xl border border-line bg-surface shadow-card">
      <div className={clsx("bg-gradient-to-b to-transparent px-4 pb-3 pt-4", tone)}>
        <div className="flex items-start gap-3">
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-surface text-2xl shadow-card" aria-hidden>{icon}</span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <StatusPill status={card.status} label={card.status_label} />
              <Pill tone="ink">{stateLabel(card.state, lang) ?? t("central")}</Pill>
            </div>
            <h3 className="mt-1.5 text-[1.12rem] font-bold leading-tight">{card.name}</h3>
            <p className="text-[.92rem] leading-snug text-ink-2">{card.tagline}</p>
          </div>
        </div>
      </div>
      <div className="px-4 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-3">{t("benefit")}</p>
          {card.amount ? (
            <p className="flex flex-wrap items-baseline gap-x-1.5 text-2xl font-extrabold leading-tight text-peacock"><CountUp value={card.amount} />
              {card.unit && <span className="text-sm font-semibold text-ink-3">{card.unit}</span>}</p>
          ) : <p className="font-semibold leading-snug text-peacock">{card.benefit}</p>}
        </div>
        <div className="mt-2 flex items-center gap-2 text-xs text-ink-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink/[.07]">
            <motion.div className={clsx("h-full rounded-full", card.status === "eligible" ? "bg-leaf" : card.status === "maybe" ? "bg-marigold" : "bg-coral")}
              initial={{ width: 0 }} animate={{ width: `${(100 * passed) / Math.max(card.rules.length, 1)}%` }} transition={{ duration: 0.8, delay: 0.2 }} />
          </div>
          <span className="shrink-0">{t("passed", { p: passed, n: card.rules.length })}</span>
        </div>
        {card.amount ? <p className="mt-1 text-[.9rem] text-ink-2">{card.benefit}</p> : null}
        <FreshnessBadge card={card} />
        <WhatIfNote card={card} />

        {!compact && (
          <>
            <button onClick={() => setOpen((o) => !o)} aria-expanded={open}
              className="mt-3 flex min-h-12 w-full items-center justify-between rounded-2xl bg-surface-2 px-3.5 font-semibold text-ink-2 hover:text-ink">
              <span>{t("rulesChecklist")}</span>
              <motion.span animate={{ rotate: open ? 180 : 0 }}><ChevronDown size={20} /></motion.span>
            </button>
            <AnimatePresence initial={false}>
              {open && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={spring} className="overflow-hidden">
                  <div className="pt-1"><RuleChecklist rules={card.rules} citations={citations} msgKey={msgKey} /></div>
                  <p className="mt-2 text-sm font-semibold text-ink-2">{t("documentsToBring")}</p>
                  <p className="text-[.92rem] text-ink-2">{card.documents.map((d) => d.label).join(" · ")}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}

        <div className="mt-3 flex items-center gap-2">
          <Link href={`/scheme/${card.scheme_id}`} className="inline-flex min-h-12 flex-1 items-center justify-center rounded-2xl bg-peacock px-4 font-semibold text-white shadow-card hover:brightness-110 dark:text-[#06242b]">
            {t("viewDetails")}
          </Link>
          <motion.button ref={saveRef} whileTap={{ scale: 0.9 }} onClick={() => toggleSave(card, saved ? null : saveRef.current?.getBoundingClientRect())}
            aria-pressed={saved} aria-label={saved ? t("saved") : t("save")}
            className={clsx("grid h-12 w-12 place-items-center rounded-2xl border transition-colors", saved ? "border-marigold bg-marigold-soft text-[#9a5b00] dark:text-marigold" : "border-line text-ink-2 hover:bg-surface-2")}>
            {saved ? <BookmarkCheck size={22} /> : <Bookmark size={22} />}
          </motion.button>
          <a href={card.official_url} target="_blank" rel="noreferrer" aria-label={t("official")}
            className="grid h-12 w-12 place-items-center rounded-2xl border border-line text-ink-2 hover:bg-surface-2"><ExternalLink size={20} /></a>
        </div>
        <p className="mt-2 text-[.78rem] text-ink-3">{t("lastVerified", { d: card.last_verified })}</p>
      </div>
    </motion.article>
  );
}
