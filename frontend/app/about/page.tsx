"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";
import { useApp } from "@/lib/app-context";
import { getJSON } from "@/lib/api";
import type { SchemeCard } from "@/lib/types";
import Gajju from "@/components/Gajju";
import { Ant, Chameleon, Owl, Parrot, Peacock } from "@/components/animals";
import { Pill } from "@/components/ui";
import { stateLabel } from "@/components/SchemeParts";
import { pageIn, rowIn, stagger } from "@/animations/motion";

interface Meta {
  schemes: number; documents: number; chunks: number; states: string[]; central: number; last_verified: string;
  changed: { scheme_id: string; name: Record<string, string>; changed_on: string; note: Record<string, string> | null }[];
  engine: { embedder: string; reranker: string; llm: boolean; retrieval: string; crosslingual: string };
}

const STEPS = [
  { icon: <Parrot size={44} talking={false} />, en: ["Understand", "Detects Telugu, Hindi, English, Hinglish/Tenglish and picks out facts like “2 acres” or “1.5 lakh”."],
    te: ["అర్థం చేసుకోవడం", "తెలుగు, హిందీ, ఇంగ్లీష్, టెంగ్లీష్‌ను గుర్తించి “2 ఎకరాలు”, “1.5 లక్షలు” లాంటి వివరాలను తీసుకుంటుంది."],
    hi: ["समझना", "तेलुगु, हिंदी, अंग्रेज़ी, हिंग्लिश पहचानता है और “2 एकड़”, “1.5 लाख” जैसी बातें निकालता है।"] },
  { icon: <Ant size={44} />, en: ["Search", "Ants search official guidelines with keyword + meaning search, then put the best pages first."],
    te: ["వెతకడం", "చీమలు అధికారిక మార్గదర్శకాలను పదాలు + అర్థం ఆధారంగా వెతికి, ఉత్తమ పేజీలను ముందు పెడతాయి."],
    hi: ["खोज", "चींटियाँ आधिकारिक दिशानिर्देशों में शब्द + अर्थ से खोजती हैं और सबसे सही पन्ने आगे रखती हैं।"] },
  { icon: <Gajju size={48} state="nod" decorative />, en: ["Decide with rules", "Plain code, not AI, checks every rule (income, age, land) and marks ✅ / ❌ / ❓."],
    te: ["నియమాలతో నిర్ణయం", "AI కాదు, సాధారణ కోడ్ ప్రతి నియమాన్ని (ఆదాయం, వయస్సు, భూమి) తనిఖీ చేసి ✅ / ❌ / ❓ ఇస్తుంది."],
    hi: ["नियमों से फ़ैसला", "AI नहीं, साधारण कोड हर नियम (आय, उम्र, ज़मीन) जाँचता है और ✅ / ❌ / ❓ देता है।"] },
  { icon: <Owl size={44} />, en: ["Verify", "The owl checks every citation against the source. Unsupported claims are removed; if unsure, Haathi says so."],
    te: ["ధృవీకరణ", "గుడ్లగూబ ప్రతి మూలాన్ని తనిఖీ చేస్తుంది. ఆధారం లేని మాటలు తొలగిస్తుంది; ఖచ్చితం కాకపోతే హాథీ అదే చెబుతుంది."],
    hi: ["सत्यापन", "उल्लू हर स्रोत की जाँच करता है। बिना आधार की बातें हटती हैं; पक्का न हो तो हाथी साफ़ बताता है।"] },
  { icon: <Peacock size={56} play={false} />, en: ["Show", "The peacock shows your schemes with documents to bring and how to apply."],
    te: ["చూపించడం", "నెమలి మీ పథకాలను, కావాల్సిన పత్రాలు, దరఖాస్తు విధానంతో చూపిస్తుంది."],
    hi: ["दिखाना", "मोर आपकी योजनाएँ ज़रूरी दस्तावेज़ और आवेदन के तरीके के साथ दिखाता है।"] },
];

export default function About() {
  const { t, lang } = useApp();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [schemes, setSchemes] = useState<SchemeCard[]>([]);
  useEffect(() => {
    getJSON<Meta>("/api/meta").then(setMeta).catch(() => {});
    getJSON<{ schemes: SchemeCard[] }>(`/api/schemes?lang=${lang}`).then((r) => setSchemes(r.schemes)).catch(() => {});
  }, [lang]);

  return (
    <motion.div variants={pageIn} initial="hidden" animate="show" className="mx-auto max-w-3xl px-4 pb-12 pt-4">
      <h1 className="text-2xl font-extrabold tracking-tight">{t("aboutTitle")}</h1>

      <div className="mt-4 flex items-start gap-3 rounded-3xl border-2 border-marigold/50 bg-amber-soft/70 p-4">
        <ShieldCheck className="mt-0.5 shrink-0 text-[#9a5b00] dark:text-marigold" />
        <p className="font-medium leading-snug">{t("disclaimer")} {t("privacyNote")}</p>
      </div>

      {meta && (
        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          {[[meta.schemes, lang === "te" ? "పథకాలు" : lang === "hi" ? "योजनाएँ" : "schemes"], [meta.documents, lang === "te" ? "పత్రాలు" : lang === "hi" ? "दस्तावेज़" : "documents"],
            [meta.last_verified, lang === "te" ? "చివరి తనిఖీ" : lang === "hi" ? "अंतिम जाँच" : "last verified"]].map(([n, l]) => (
            <div key={String(l)} className="rounded-2xl bg-surface p-3 shadow-card"><div className={`${String(n).includes("-") ? "text-base" : "text-xl"} whitespace-nowrap font-extrabold text-peacock`}>{n}</div><div className="text-xs text-ink-3">{l}</div></div>
          ))}
        </div>
      )}

      <h2 className="mt-8 text-lg font-bold">{lang === "te" ? "హాథీ ఎలా పనిచేస్తుంది" : lang === "hi" ? "हाथी कैसे काम करता है" : "How Haathi works"}</h2>
      <motion.ol variants={stagger(0.1)} initial="hidden" whileInView="show" viewport={{ once: true }} className="mt-3 space-y-2">
        {STEPS.map((s, i) => (
          <motion.li key={i} variants={rowIn} className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-3">
            <span className="grid h-14 w-14 shrink-0 place-items-center">{s.icon}</span>
            <div><p className="font-bold">{i + 1}. {s[lang][0]}</p><p className="text-[.95rem] leading-snug text-ink-2">{s[lang][1]}</p></div>
          </motion.li>
        ))}
      </motion.ol>

      {meta && meta.changed.length > 0 && (
        <>
          <h2 className="mt-8 flex items-center gap-2 text-lg font-bold"><Chameleon size={40} /> {lang === "te" ? "ఇటీవల మారిన నియమాలు" : lang === "hi" ? "हाल में बदले नियम" : "Recently changed rules"}</h2>
          <ul className="mt-2 space-y-2">
            {meta.changed.map((c) => (
              <li key={c.scheme_id}><Link href={`/scheme/${c.scheme_id}`} className="block rounded-2xl bg-surface p-3 hover:bg-surface-2">
                <span className="font-semibold">{c.name[lang] ?? c.name.en}</span> <Pill tone="peacock">{c.changed_on}</Pill>
                {c.note && <p className="text-sm text-ink-2">{c.note[lang] ?? c.note.en}</p>}
              </Link></li>
            ))}
          </ul>
        </>
      )}

      <h2 className="mt-8 text-lg font-bold">{t("sources")} · {schemes.length}</h2>
      <ul className="mt-2 divide-y divide-line overflow-hidden rounded-3xl border border-line bg-surface">
        {schemes.map((s) => (
          <li key={s.scheme_id} className="flex items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1">
              <Link href={`/scheme/${s.scheme_id}`} className="font-semibold hover:text-peacock">{s.name}</Link>
              <p className="text-xs text-ink-3">{stateLabel(s.state, lang) ?? t("central")} · {t("lastVerified", { d: s.last_verified })}{s.changed_on ? ` · 🦎 ${s.changed_on}` : ""}</p>
            </div>
            <a href={s.official_url} target="_blank" rel="noreferrer" aria-label={`${t("official")}: ${s.name}`} className="grid h-11 w-11 place-items-center rounded-full text-peacock hover:bg-peacock-soft"><ExternalLink size={18} /></a>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs leading-relaxed text-ink-3">
        {t("seedNotice")} {meta && `Engine: ${meta.engine.retrieval} retrieval · ${meta.engine.embedder} · ${meta.engine.reranker} · LLM ${meta.engine.llm ? "on" : "off"}.`}
        {" "}Haathi does not use government logos and is not affiliated with any government. · <Link href="/playground" className="underline">Animation playground</Link>
      </p>
    </motion.div>
  );
}
