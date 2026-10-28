// Shared Motion presets (haathi.md §9.4). Keep durations short: animations never delay content.
import type { Transition, Variants } from "motion/react";

export const spring: Transition = { type: "spring", stiffness: 420, damping: 32, mass: 0.8 };
export const softSpring: Transition = { type: "spring", stiffness: 220, damping: 24 };
export const bouncy: Transition = { type: "spring", stiffness: 520, damping: 14 };

/** Message appear: fade + 8px slide up, spring. */
export const messageIn: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: spring },
};

/** Staggered lists (rule rows, document rows). */
export const stagger = (step = 0.07, delay = 0): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: step, delayChildren: delay } },
});

export const rowIn: Variants = {
  hidden: { opacity: 0, x: -6 },
  show: { opacity: 1, x: 0, transition: spring },
};

/** Tick bounce for ✅/❌ marks. */
export const tickIn: Variants = {
  hidden: { scale: 0, rotate: -30 },
  show: { scale: [0, 1.25, 1], rotate: 0, transition: { duration: 0.38, times: [0, 0.6, 1] } },
};

/** Peacock reveal: cards spread out from the centre like feathers. */
export const featherFan = (i: number, n: number): Variants => {
  const mid = (n - 1) / 2;
  const angle = (i - mid) * 7;
  return {
    hidden: { opacity: 0, y: 24, rotate: angle * 1.6, scale: 0.86, transformOrigin: "50% 140%" },
    show: { opacity: 1, y: 0, rotate: 0, scale: 1, transition: { ...softSpring, delay: 0.12 + Math.abs(i - mid) * 0.09 } },
  };
};

/** Buttons: press scale 0.97, spring back. */
export const press = { whileTap: { scale: 0.97 }, transition: spring };

/** Language switch: crossfade with a slight blur between scripts. */
export const scriptSwap: Variants = {
  initial: { opacity: 0, filter: "blur(4px)" },
  animate: { opacity: 1, filter: "blur(0px)", transition: { duration: 0.28 } },
  exit: { opacity: 0, filter: "blur(4px)", transition: { duration: 0.18 } },
};

/** Error: small horizontal shake. */
export const shake = { x: [0, -8, 8, -6, 6, -3, 3, 0], transition: { duration: 0.45 } };

export const pageIn: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] } },
};
