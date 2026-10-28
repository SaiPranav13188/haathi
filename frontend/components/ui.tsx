"use client";

import { AnimatePresence, animate, motion, useMotionValue, useTransform, type HTMLMotionProps } from "motion/react";
import { forwardRef, useEffect, useId, useState, type ReactNode } from "react";
import clsx from "clsx";
import { X } from "lucide-react";
import { useApp } from "@/lib/app-context";
import { spring } from "@/animations/motion";

type BtnProps = HTMLMotionProps<"button"> & { variant?: "primary" | "secondary" | "ghost" | "marigold" | "danger"; size?: "md" | "lg" | "sm" };

export const Button = forwardRef<HTMLButtonElement, BtnProps>(function Button({ variant = "primary", size = "md", className, children, ...rest }, ref) {
  return (
    <motion.button ref={ref} whileTap={{ scale: 0.97 }} transition={spring}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-2xl font-semibold transition-colors disabled:opacity-50 disabled:pointer-events-none",
        size === "lg" && "min-h-14 px-6 text-[1.05rem]", size === "md" && "min-h-12 px-5", size === "sm" && "min-h-10 px-3.5 text-sm",
        variant === "primary" && "bg-peacock text-white shadow-card hover:brightness-110 dark:text-[#06242b]",
        variant === "marigold" && "bg-marigold text-[#3a2600] shadow-card hover:brightness-105",
        variant === "secondary" && "bg-surface text-ink border border-line hover:bg-surface-2",
        variant === "ghost" && "text-peacock hover:bg-peacock-soft",
        variant === "danger" && "bg-coral text-white hover:brightness-110",
        className)} {...rest}>
      {children}
    </motion.button>
  );
});

export function IconButton({ label, children, className, ...rest }: HTMLMotionProps<"button"> & { label: string }) {
  return (
    <motion.button whileTap={{ scale: 0.92 }} transition={spring} aria-label={label} title={label}
      className={clsx("grid h-12 w-12 place-items-center rounded-full text-ink-2 hover:bg-ink/5 hover:text-ink", className)} {...rest}>
      {children}
    </motion.button>
  );
}

/** Segmented control with a sliding pill (used for the language switcher and settings). */
export function Segmented<T extends string>({ value, options, onChange, label, size = "md" }: {
  value: T; options: { value: T; label: ReactNode; aria?: string }[]; onChange: (v: T) => void; label: string; size?: "sm" | "md";
}) {
  const id = useId();
  return (
    <div role="radiogroup" aria-label={label} className="relative flex rounded-full bg-ink/[.06] p-1">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button key={o.value} role="radio" aria-checked={active} aria-label={o.aria}
            onClick={() => onChange(o.value)}
            className={clsx("relative z-0 flex-1 rounded-full font-semibold transition-colors",
              size === "sm" ? "h-9 min-w-10 px-2.5 text-[.95rem]" : "h-11 min-w-12 px-4",
              active ? "text-white dark:text-[#06242b]" : "text-ink-2 hover:text-ink")}>
            {active && <motion.span layoutId={`seg-${id}`} className="absolute inset-0 -z-10 rounded-full bg-peacock shadow-card" transition={spring} />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

/** Benefit amount counts up (₹0 → ₹6,000). */
export function CountUp({ value, prefix = "₹", className }: { value: number; prefix?: string; className?: string }) {
  const { motionOK } = useApp();
  const mv = useMotionValue(motionOK ? 0 : value);
  const text = useTransform(mv, (v) => prefix + Math.round(v).toLocaleString("en-IN"));
  useEffect(() => {
    if (!motionOK) { mv.set(value); return; }
    const c = animate(mv, value, { duration: 1.1, ease: [0.16, 1, 0.3, 1] });
    return () => c.stop();
  }, [value, motionOK, mv]);
  return <motion.span className={clsx("tabular-nums", className)} aria-label={prefix + value.toLocaleString("en-IN")}>{text}</motion.span>;
}

export function Toasts() {
  const { toasts, dismissToast } = useApp();
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-[calc(88px+env(safe-area-inset-bottom))] z-[60] flex flex-col items-center gap-2 px-4 lg:bottom-6"
      role="status" aria-live="polite">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div key={t.id} layout initial={{ opacity: 0, y: 24, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }} transition={spring}
            className="pointer-events-auto relative w-full max-w-sm overflow-hidden rounded-2xl bg-ink text-sand shadow-lift">
            <div className="flex items-center gap-3 px-4 py-3">
              {t.icon && <span className="text-xl" aria-hidden>{t.icon}</span>}
              <span className="flex-1 text-[.95rem]">{t.text}</span>
              <button onClick={() => dismissToast(t.id)} className="grid h-8 w-8 place-items-center rounded-full hover:bg-white/10" aria-label="Dismiss">
                <X size={16} />
              </button>
            </div>
            <motion.div className={clsx("h-1", t.tone === "warn" ? "bg-coral" : t.tone === "info" ? "bg-peacock" : "bg-marigold")}
              initial={{ width: "100%" }} animate={{ width: "0%" }} transition={{ duration: 3.6, ease: "linear" }} />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

/** Bottom sheet on phones, side panel on desktop. */
export function Sheet({ open, onClose, children, title, side = false }: { open: boolean; onClose: () => void; children: ReactNode; title: string; side?: boolean }) {
  const { t } = useApp();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-50" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <div className="absolute inset-0 bg-[#0b1418]/45 backdrop-blur-[2px]" onClick={onClose} />
          <motion.div role="dialog" aria-modal aria-label={title}
            className={clsx("absolute flex flex-col bg-surface shadow-lift",
              side ? "inset-y-0 right-0 w-full max-w-xl" : "inset-x-0 bottom-0 max-h-[92dvh] rounded-t-[28px]")}
            initial={side ? { x: "100%" } : { y: "100%" }} animate={side ? { x: 0 } : { y: 0 }} exit={side ? { x: "100%" } : { y: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 38 }}
            drag={side ? false : "y"} dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_, info) => { if (info.offset.y > 120 || info.velocity.y > 600) onClose(); }}>
            {!side && <div className="mx-auto mt-2.5 h-1.5 w-12 rounded-full bg-ink/15" aria-hidden />}
            <div className="flex items-center justify-between gap-2 px-5 pb-2 pt-3">
              <h2 className="text-lg font-bold leading-tight">{title}</h2>
              <IconButton label={t("close")} onClick={onClose}><X size={22} /></IconButton>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-[max(20px,env(safe-area-inset-bottom))]">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function useMediaQuery(q: string): boolean {
  const [m, setM] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(q);
    setM(mq.matches);
    const f = () => setM(mq.matches);
    mq.addEventListener("change", f);
    return () => mq.removeEventListener("change", f);
  }, [q]);
  return m;
}

export function Pill({ tone, children, className }: { tone: "leaf" | "amber" | "coral" | "peacock" | "ink"; children: ReactNode; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[.8rem] font-semibold leading-none",
      tone === "leaf" && "bg-leaf-soft text-leaf", tone === "amber" && "bg-amber-soft text-[#9a5b00] dark:text-marigold",
      tone === "coral" && "bg-coral-soft text-coral", tone === "peacock" && "bg-peacock-soft text-peacock",
      tone === "ink" && "bg-ink/[.06] text-ink-2", className)}>{children}</span>
  );
}
