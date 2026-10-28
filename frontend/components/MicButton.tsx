"use client";

import { AnimatePresence, motion } from "motion/react";
import clsx from "clsx";
import { Mic, Square } from "lucide-react";
import { useApp } from "@/lib/app-context";

/** Mic button shaped like Gajju's ear; it ripples with the voice level (§9.3 #15). */
export default function MicButton({ listening, level, onClick, size = 56 }: { listening: boolean; level: number; onClick: () => void; size?: number }) {
  const { t, motionOK } = useApp();
  return (
    <motion.button type="button" onClick={onClick} whileTap={{ scale: 0.92 }}
      aria-label={listening ? t("stop") : t("tapToSpeak")} aria-pressed={listening}
      className="relative grid shrink-0 place-items-center" style={{ width: size, height: size }}>
      <AnimatePresence>
        {listening && motionOK && [0, 1, 2].map((i) => (
          <motion.span key={i} className="absolute inset-0 rounded-full border-2 border-peacock"
            initial={{ scale: 1, opacity: 0.6 }} animate={{ scale: 1.25 + level * 0.9 + i * 0.18, opacity: 0 }}
            exit={{ opacity: 0 }} transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.3 }} />
        ))}
      </AnimatePresence>
      <svg viewBox="0 0 64 64" className="absolute inset-0" aria-hidden>
        <motion.path
          d="M50 8 C 30 0, 6 10, 6 34 C 6 52, 22 62, 38 58 C 48 55, 52 46, 58 36 C 62 26, 60 14, 50 8 Z"
          className={clsx(listening ? "fill-peacock" : "fill-[var(--elephant-dark)]")}
          animate={{ scale: listening ? 1 + level * 0.12 : 1 }} style={{ transformOrigin: "32px 32px", transformBox: "view-box" }} />
        <path d="M46 14 C 32 8, 14 16, 14 34 C 14 46, 24 52, 34 50 C 42 48, 46 42, 50 34 C 53 26, 52 18, 46 14 Z"
          fill={listening ? "#9fe1ec" : "#f3b9c4"} opacity=".9" />
      </svg>
      <span className={clsx("relative", listening ? "text-[#06242b]" : "text-[#5a2733]")}>
        {listening ? <Square size={18} fill="currentColor" /> : <Mic size={22} strokeWidth={2.4} />}
      </span>
    </motion.button>
  );
}
