"use client";

import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";
import { useApp } from "@/lib/app-context";
import type { Lang } from "@/lib/types";
import Gajju from "@/components/Gajju";
import { AntTrail, Owl, Peacock } from "@/components/animals";
import { Button } from "@/components/ui";
import { scriptSwap } from "@/animations/motion";

const LANGS: { value: Lang; big: string; name: string; hello: string }[] = [
  { value: "te", big: "అ", name: "తెలుగు", hello: "నమస్తే" },
  { value: "hi", big: "अ", name: "हिंदी", hello: "नमस्ते" },
  { value: "en", big: "A", name: "English", hello: "Hello" },
];

export default function Welcome() {
  const { t, lang, setLang, setOnboarded, motionOK } = useApp();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [dir, setDir] = useState(1);
  const go = (n: number) => { setDir(n > step ? 1 : -1); setStep(n); };
  const finish = () => { setOnboarded(true); router.replace("/"); };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" && step < 3) go(step + 1);
      if (e.key === "ArrowLeft" && step > 0) go(step - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const slides = [
    { title: t("slide1Title"), body: t("slide1Body"), art: <div className="w-64"><AntTrail count={6} /><div className="mt-2 flex justify-center"><Gajju state="thinking" size={130} /></div></div> },
    { title: t("slide2Title"), body: t("slide2Body"), art: <div className="flex items-end gap-2"><Owl size={130} /><div className="mb-6 space-y-1.5">{[1, 2, 3].map((i) => (
      <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 + i * 0.35 }}
        className="flex items-center gap-1.5 rounded-full bg-leaf-soft px-3 py-1.5 text-sm font-semibold text-leaf">[{i}] ✓</motion.div>))}</div></div> },
    { title: t("slide3Title"), body: t("slide3Body"), art: <Peacock size={230} /> },
  ];

  return (
    <div className="paper-texture relative flex min-h-dvh flex-col overflow-hidden bg-sand">
      <div className="flex items-center justify-between px-5 pt-[max(16px,env(safe-area-inset-top))]">
        <div className="flex gap-1.5" aria-label={`Step ${step + 1} of 4`}>
          {[0, 1, 2, 3].map((i) => (
            <motion.span key={i} className="h-2 rounded-full" animate={{ width: i === step ? 26 : 8, backgroundColor: i <= step ? "var(--peacock)" : "var(--line)" }} />
          ))}
        </div>
        {step > 0 && <button onClick={finish} className="h-11 rounded-full px-4 font-semibold text-ink-3 hover:bg-ink/5">{t("skip")}</button>}
      </div>

      <AnimatePresence mode="wait" custom={dir}>
        {step === 0 ? (
          <motion.section key="lang" className="flex flex-1 flex-col items-center px-6 pb-8 pt-4 text-center"
            initial={{ opacity: 0, x: 40 * dir }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 * dir }}>
            <Gajju state="wave" size={170} />
            <AnimatePresence mode="wait">
              <motion.div key={lang} variants={scriptSwap} initial="initial" animate="animate" exit="exit">
                <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-peacock">{LANGS.find((l) => l.value === lang)?.hello}! {t("appName")}</h1>
                <p className="mx-auto mt-1 max-w-sm text-ink-2">{t("tagline")}</p>
              </motion.div>
            </AnimatePresence>
            <h2 className="mt-8 text-sm font-bold uppercase tracking-widest text-ink-3">{t("chooseLang")}</h2>
            <div className="mt-3 grid w-full max-w-md grid-cols-3 gap-3" role="radiogroup" aria-label={t("chooseLang")}>
              {LANGS.map((l) => (
                <motion.button key={l.value} role="radio" aria-checked={lang === l.value} onClick={() => setLang(l.value)} whileTap={{ scale: 0.95 }}
                  className={clsx("relative flex aspect-[4/5] flex-col items-center justify-center gap-1 rounded-3xl border-2 bg-surface shadow-card transition-colors",
                    lang === l.value ? "border-peacock" : "border-transparent hover:border-line")}>
                  <span className={clsx("text-5xl font-extrabold", lang === l.value ? "text-peacock" : "text-ink-2")}>{l.big}</span>
                  <span className="font-semibold">{l.name}</span>
                  {lang === l.value && <motion.span layoutId="lang-check" className="absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-full bg-peacock text-sm font-bold text-white">✓</motion.span>}
                </motion.button>
              ))}
            </div>
            <div className="flex-1" />
            <Button size="lg" className="mt-8 w-full max-w-md" onClick={() => go(1)}>{t("continue")}</Button>
          </motion.section>
        ) : (
          <motion.section key={step} className="flex flex-1 flex-col items-center px-6 pb-8 pt-6 text-center"
            initial={{ opacity: 0, x: 60 * dir }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -60 * dir }}
            drag={motionOK ? "x" : false} dragConstraints={{ left: 0, right: 0 }} dragElastic={0.25}
            onDragEnd={(_, info) => { if (info.offset.x < -70 && step < 3) go(step + 1); if (info.offset.x > 70) go(step - 1); }}>
            <div className="grid h-72 w-full place-items-center">{slides[step - 1].art}</div>
            <h1 className="mt-4 text-[1.7rem] font-extrabold leading-tight tracking-tight">{slides[step - 1].title}</h1>
            <p className="mx-auto mt-2 max-w-md text-[1.05rem] text-ink-2">{slides[step - 1].body}</p>
            {step === 3 && <p className="mx-auto mt-5 max-w-md rounded-2xl bg-peacock-soft/70 px-4 py-3 text-sm text-ink-2">🔒 {t("privacyNote")}</p>}
            <div className="flex-1" />
            <div className="mt-8 flex w-full max-w-md gap-3">
              <Button size="lg" variant="secondary" className="flex-1" onClick={() => go(step - 1)}>{t("back")}</Button>
              <Button size="lg" className="flex-[2]" onClick={() => (step < 3 ? go(step + 1) : finish())}>{step < 3 ? t("next") : t("start")}</Button>
            </div>
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  );
}
