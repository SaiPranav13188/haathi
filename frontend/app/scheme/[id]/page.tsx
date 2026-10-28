"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { use, useEffect, useRef, useState } from "react";
import { ArrowLeft, Bookmark, BookmarkCheck, ExternalLink } from "lucide-react";
import { useApp } from "@/lib/app-context";
import { postJSON, profileValues } from "@/lib/api";
import type { Citation, RuleRow, SchemeCard } from "@/lib/types";
import Gajju, { type GajjuState } from "@/components/Gajju";
import { CAT_ICON, stateLabel, CitationChip, DocumentChecklist, FreshnessBadge, RuleChecklist, StatusPill, WhatIfNote } from "@/components/SchemeParts";
import { SourcePage } from "@/components/SourceViewer";
import { CountUp, Pill } from "@/components/ui";
import { pageIn } from "@/animations/motion";

export default function SchemeDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { t, lang, profile, isSaved, toggleSave, saved, ready } = useApp();
  const [data, setData] = useState<{ card: SchemeCard; citations: Citation[]; disclaimer: string } | null>(null);
  const [err, setErr] = useState(false);
  const [nod, setNod] = useState<GajjuState>("idle");
  const saveRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!ready) return; // wait for the on-device profile to load
    setErr(false);
    postJSON<{ card: SchemeCard; citations: Citation[]; disclaimer: string }>(`/api/schemes/${id}`, { profile: profileValues(profile), lang })
      .then(setData)
      .catch(() => {
        // offline: fall back to the saved copy
        const s = saved.find((x) => x.scheme_id === id);
        if (s) setData({ card: s, citations: [], disclaimer: t("disclaimer") }); else setErr(true);
      });
  }, [id, lang, ready, profile]); // eslint-disable-line react-hooks/exhaustive-deps

  if (err) return <div className="p-6 text-center"><Gajju state="error" size={120} /><p className="mt-2">{t("errorBody")}</p></div>;
  if (!data) return <div className="mx-auto max-w-3xl space-y-3 p-4">{[0, 1, 2].map((i) => <div key={i} className="shimmer h-32 rounded-3xl" />)}</div>;
  const { card, citations } = data;
  const byId = new Map(citations.map((c) => [c.id, c]));
  const onRow = (r: RuleRow) => { setNod(r.result === "pass" ? "nod" : r.result === "unknown" ? "tilt" : "not_eligible"); setTimeout(() => setNod("idle"), 650); };
  const s = isSaved(card.scheme_id);

  return (
    <motion.div variants={pageIn} initial="hidden" animate="show" className="mx-auto max-w-3xl px-4 pb-12 pt-3">
      <Link href="/" onClick={(e) => { if (history.length > 1) { e.preventDefault(); history.back(); } }}
        className="inline-flex h-11 items-center gap-1.5 rounded-full pr-3 font-semibold text-ink-2 hover:text-ink"><ArrowLeft size={20} />{t("back")}</Link>

      <motion.header layoutId={`card-detail-${card.scheme_id}`} className="mt-1 rounded-3xl border border-line bg-surface p-5 shadow-card">
        <div className="flex items-start gap-3">
          <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-surface-2 text-3xl" aria-hidden>{CAT_ICON[card.categories[0]] ?? "📄"}</span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap gap-1.5"><StatusPill status={card.status} label={card.status_label} /><Pill tone="ink">{stateLabel(card.state, lang) ?? t("central")}</Pill></div>
            <h1 className="mt-1.5 text-2xl font-extrabold leading-tight">{card.name}</h1>
            <p className="text-ink-2">{card.tagline}</p>
          </div>
        </div>
        <div className="mt-4 rounded-2xl bg-peacock-soft/60 p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-ink-3">{t("benefit")}</p>
          {card.amount ? <p className="text-3xl font-extrabold text-peacock"><CountUp value={card.amount} /><span className="ml-1.5 text-base font-semibold text-ink-3">{card.unit}</span></p> : null}
          <p className="mt-0.5 font-medium">{card.benefit} {byId.get(card.benefit_citation) && <CitationChip c={byId.get(card.benefit_citation)!} msgKey="detail" />}</p>
        </div>
        <FreshnessBadge card={card} />
        <WhatIfNote card={card} />
        <div className="mt-4 flex gap-2">
          <motion.button ref={saveRef} whileTap={{ scale: 0.95 }} onClick={() => toggleSave(card, s ? null : saveRef.current?.getBoundingClientRect())}
            className={`inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded-2xl border font-semibold ${s ? "border-marigold bg-marigold-soft" : "border-line"}`}>
            {s ? <BookmarkCheck size={20} /> : <Bookmark size={20} />}{s ? t("saved") : t("save")}
          </motion.button>
          <a href={card.official_url} target="_blank" rel="noreferrer" className="inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded-2xl bg-peacock font-semibold text-white dark:text-[#06242b]">
            {t("official")} <ExternalLink size={18} /></a>
        </div>
      </motion.header>

      <section className="mt-5 rounded-3xl border border-line bg-surface p-5 shadow-card">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">{t("rulesChecklist")}</h2>
          <Gajju state={nod} size={56} decorative />
        </div>
        <RuleChecklist rules={card.rules} citations={citations} onRowShown={onRow} msgKey="detail" />
      </section>

      <section className="mt-5 rounded-3xl border border-line bg-surface p-5 shadow-card">
        <h2 className="mb-3 text-lg font-bold">🐝 {t("documentsToBring")}</h2>
        <DocumentChecklist schemeId={card.scheme_id} documents={card.documents} />
      </section>

      <section className="mt-5 rounded-3xl border border-line bg-surface p-5 shadow-card">
        <h2 className="mb-2 text-lg font-bold">{t("howToApply")}</h2>
        <p className="leading-relaxed">{card.how_to_apply}</p>
        {byId.get(card.apply_citation) && <div className="mt-2"><CitationChip c={byId.get(card.apply_citation)!} msgKey="detail" /></div>}
      </section>

      {card.official_sources && card.official_sources.length > 0 && (
        <section className="mt-5 rounded-3xl border border-leaf/30 bg-leaf-soft/40 p-5 shadow-card">
          <h2 className="text-lg font-bold">📜 {t("officialDocs")}</h2>
          <p className="mb-2 text-sm text-ink-2">{t("officialDocsNote")}</p>
          <ul className="space-y-1.5">
            {card.official_sources.map((o) => (
              <li key={o.doc} className="flex items-center gap-2">
                <span className="min-w-0 flex-1 text-[.95rem] font-medium">{o.label}{o.downloaded ? <span className="text-ink-3"> · {o.downloaded}</span> : null}</span>
                <a href={`/api/files/${encodeURIComponent(o.doc)}`} target="_blank" rel="noreferrer" className="inline-flex h-10 items-center gap-1 rounded-full bg-surface px-3 text-sm font-semibold text-peacock">PDF <ExternalLink size={14} /></a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {byId.get(card.benefit_citation) && (
        <section className="mt-5 rounded-3xl border border-line bg-surface p-5 shadow-card">
          <h2 className="mb-3 text-lg font-bold">🦉 {t("sources")}</h2>
          <SourcePage citation={byId.get(card.benefit_citation)!} />
        </section>
      )}
      <p className="mt-4 text-sm text-ink-3">⚠️ {data.disclaimer} · {t("lastVerified", { d: card.last_verified })}</p>
    </motion.div>
  );
}
