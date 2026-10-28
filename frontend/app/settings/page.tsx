"use client";

import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { useApp } from "@/lib/app-context";
import type { AnimLevel } from "@/lib/types";
import Gajju from "@/components/Gajju";
import { LanguageSwitch } from "@/components/AppShell";
import { Button, Segmented } from "@/components/ui";
import { pageIn } from "@/animations/motion";

function Row({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-b border-line py-4 last:border-0 sm:flex-row sm:items-center sm:justify-between">
      <div><p className="font-semibold">{label}</p>{hint && <p className="text-sm text-ink-3">{hint}</p>}</div>
      <div className="sm:min-w-72">{children}</div>
    </div>
  );
}

export default function Settings() {
  const { t, anim, setAnim, theme, setTheme, textSize, setTextSize, clearData, toast, profile, reducedMotion, lang } = useApp();
  const [confirm, setConfirm] = useState(false);
  const [recorder, setRecorder] = useState(false); // dev-only tool; the production backend refuses it
  useEffect(() => { fetch("/api/asr-clips").then((r) => setRecorder(r.ok)).catch(() => {}); }, []);
  return (
    <motion.div variants={pageIn} initial="hidden" animate="show" className="mx-auto max-w-2xl px-4 pb-12 pt-4">
      <div className="flex items-center gap-3"><Gajju state={anim === "off" ? "idle" : "wave"} size={72} /><h1 className="text-2xl font-extrabold">{t("settings")}</h1></div>
      <div className="mt-4 rounded-3xl border border-line bg-surface px-5 shadow-card">
        <Row label="Language · భాష · भाषा"><LanguageSwitch size="md" /></Row>
        <Row label={t("animation")} hint={reducedMotion ? "Reduce Motion is on: movement is replaced with fades." : lang === "te" ? "పెద్దలకు ‘ప్రశాంతం’ బాగుంటుంది" : lang === "hi" ? "बुज़ुर्गों के लिए ‘शांत’ अच्छा है" : "“Calm” is gentler for older users"}>
          <Segmented<AnimLevel> label={t("animation")} value={anim} onChange={setAnim}
            options={[{ value: "full", label: t("animFull") }, { value: "calm", label: t("animCalm") }, { value: "off", label: t("animOff") }]} />
        </Row>
        <Row label={t("theme")}>
          <Segmented label={t("theme")} value={theme} onChange={setTheme}
            options={[{ value: "system", label: t("themeSystem") }, { value: "light", label: t("themeLight") }, { value: "dark", label: t("themeDark") }]} />
        </Row>
        <Row label={t("textSize")}>
          <Segmented label={t("textSize")} value={textSize} onChange={setTextSize} options={[{ value: "normal", label: t("normal") }, { value: "large", label: t("large") }]} />
        </Row>
      </div>

      {recorder && <a href="/record" className="mt-5 flex items-center gap-3 rounded-3xl border border-line bg-surface p-5 shadow-card hover:bg-surface-2">
        <span className="text-2xl" aria-hidden>🎙️</span>
        <span className="flex-1"><b className="block">Speech test recorder</b><span className="text-sm text-ink-3">Read 20 sentences per language to measure voice accuracy</span></span>
        <span aria-hidden>→</span>
      </a>}

      <div className="mt-5 rounded-3xl border border-line bg-surface p-5 shadow-card">
        <p className="font-semibold">{t("yourProfile")}</p>
        {Object.keys(profile).length === 0 ? <p className="mt-1 text-sm text-ink-3">—</p> : (
          <ul className="mt-2 grid gap-1.5 text-sm sm:grid-cols-2">
            {Object.entries(profile).map(([k, v]) => (
              <li key={k} className="rounded-xl bg-surface-2 px-3 py-2"><span className="text-ink-3">{k.replaceAll("_", " ")}:</span> <b>{String(v.value)}</b>
                {v.source_text && <span className="block text-xs text-ink-3">“{v.source_text}”</span>}</li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-sm text-ink-3">🔒 {t("privacyNote")}</p>
        {!confirm ? (
          <Button variant="danger" className="mt-4" onClick={() => setConfirm(true)}><Trash2 size={18} />{t("clearData")}</Button>
        ) : (
          <div className="mt-4 rounded-2xl bg-coral-soft p-3">
            <p className="font-medium">{t("clearConfirm")}</p>
            <div className="mt-2 flex gap-2">
              <Button variant="danger" onClick={() => { clearData(); setConfirm(false); toast(t("cleared"), "info", "🧹"); }}>{t("clearData")}</Button>
              <Button variant="secondary" onClick={() => setConfirm(false)}>{t("back")}</Button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
