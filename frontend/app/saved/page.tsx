"use client";

import { AnimatePresence, motion, useMotionValue, useTransform } from "motion/react";
import { useRef, useState } from "react";
import { useApp } from "@/lib/app-context";
import { postJSON, profileValues } from "@/lib/api";
import type { SchemeCard } from "@/lib/types";
import { Fireflies, Monkey, Squirrel } from "@/components/animals";
import { SchemeCardView } from "@/components/SchemeParts";
import { pageIn } from "@/animations/motion";

const PULL = 90;

export default function SavedPage() {
  const { t, saved, replaceSaved, online, profile, lang, motionOK, toast } = useApp();
  const y = useMotionValue(0);
  const progress = useTransform(y, [0, PULL], [0, 1]);
  const [p, setP] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const start = useRef<number | null>(null);

  // 🐒 pull to refresh: re-check saved schemes against the latest rules
  const refresh = async () => {
    if (!saved.length || !online) return;
    setRefreshing(true);
    try {
      const r = await postJSON<{ cards: SchemeCard[] }>("/api/eligibility/evaluate", { profile: profileValues(profile), lang, scheme_ids: saved.map((s) => s.scheme_id) });
      const order = new Map(saved.map((s, i) => [s.scheme_id, i]));
      replaceSaved(r.cards.sort((a, b) => (order.get(a.scheme_id) ?? 0) - (order.get(b.scheme_id) ?? 0)));
      toast("✓", "ok", "🐒");
    } catch { /* offline */ } finally { setRefreshing(false); }
  };

  return (
    <motion.div variants={pageIn} initial="hidden" animate="show"
      className="relative mx-auto min-h-[70dvh] max-w-3xl px-4 pb-10 pt-4"
      onTouchStart={(e) => { if (window.scrollY <= 0) start.current = e.touches[0].clientY; }}
      onTouchMove={(e) => {
        if (start.current == null) return;
        const d = Math.max(0, Math.min(PULL * 1.3, (e.touches[0].clientY - start.current) * 0.55));
        y.set(d); setP(progress.get());
      }}
      onTouchEnd={() => { if (y.get() >= PULL) refresh(); y.set(0); setP(0); start.current = null; }}>
      {!online && <div className="pointer-events-none fixed inset-0 -z-10 bg-[#0d1b2a]"><Fireflies count={22} /></div>}
      <AnimatePresence>
        {(p > 0.05 || refreshing) && motionOK && (
          <motion.div className="pointer-events-none absolute left-1/2 top-0 z-10 -translate-x-1/2" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            exit={{ y: -60, opacity: 0, transition: { duration: 0.35 } }}>
            <Monkey progress={refreshing ? 1 : p} />
          </motion.div>
        )}
      </AnimatePresence>
      <motion.div style={{ y }}>
        <h1 className={`text-2xl font-extrabold tracking-tight ${online ? "" : "text-[#f6efd9]"}`}>{t("savedTitle")}</h1>
        {!online && <p className="mt-1 text-[#f6efd9]/80">🌙 {t("offline")}</p>}
        {saved.length === 0 ? (
          <div className="mt-10 flex flex-col items-center text-center">
            <motion.div animate={motionOK ? { rotate: [0, -6, 6, 0], y: [0, -6, 0] } : {}} transition={{ duration: 2.4, repeat: Infinity }}><Squirrel size={110} /></motion.div>
            <p className="mt-4 max-w-sm text-ink-2">{t("savedEmpty")}</p>
          </div>
        ) : (
          <motion.div layout className="mt-4 grid gap-3 md:grid-cols-2">
            <AnimatePresence>
              {saved.map((c) => (
                <motion.div key={c.scheme_id} layout initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9, x: -40 }}
                  className={online ? "" : "rounded-3xl shadow-[0_0_30px_rgba(255,226,122,.25)]"}>
                  <SchemeCardView card={c} msgKey="saved" />
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </motion.div>
    </motion.div>
  );
}
