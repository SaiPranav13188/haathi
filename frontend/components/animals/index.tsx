"use client";

/**
 * Helper animals (haathi.md §9.3), drawn as original inline SVG and animated with Motion, so there are no
 * third-party animation licenses and no network loads (see animations/LICENSES.md). Each one stands for a
 * real system step; all are aria-hidden and paired with equivalent text by their callers.
 */
import { motion } from "motion/react";
import { useApp } from "@/lib/app-context";

const loop = (d: number, delay = 0) => ({ duration: d, repeat: Infinity, ease: "easeInOut" as const, delay });

/* ---------------------------------------------------------------- 🐜 ant */
export function Ant({ carrying = true, size = 26, flip = false, delay = 0 }: { carrying?: boolean; size?: number; flip?: boolean; delay?: number }) {
  const { motionOK } = useApp();
  return (
    <svg viewBox="0 0 40 30" width={size} height={size * 0.75} aria-hidden style={{ transform: flip ? "scaleX(-1)" : undefined, overflow: "visible" }}>
      {carrying && (
        <motion.g animate={motionOK ? { y: [0, -1, 0] } : {}} transition={loop(0.4, delay)}>
          <rect x="15" y="0" width="16" height="12" rx="2" fill="#fff" stroke="var(--peacock)" strokeWidth="1.4" />
          <rect x="18" y="3.5" width="10" height="1.6" rx=".8" fill="var(--peacock)" opacity=".6" />
          <rect x="18" y="6.8" width="7" height="1.6" rx=".8" fill="var(--peacock)" opacity=".6" />
        </motion.g>
      )}
      <g fill="#3b2417">
        <ellipse cx="9" cy="20" rx="6" ry="4.5" />
        <ellipse cx="19" cy="19" rx="4" ry="3.4" />
        <circle cx="27" cy="17.5" r="3.6" />
      </g>
      <g stroke="#3b2417" strokeWidth="1.4" strokeLinecap="round" fill="none">
        <path d="M29 15 q3 -5 6 -5" /><path d="M28 14.5 q1 -6 4 -7" />
        {[0, 1, 2].map((i) => (
          <motion.path key={i} d={`M${15 + i * 4} 21 l ${-2 + i} 6`}
            animate={motionOK ? { rotate: i % 2 ? [-18, 18, -18] : [18, -18, 18] } : {}}
            style={{ transformOrigin: `${15 + i * 4}px 21px`, transformBox: "view-box" }} transition={loop(0.32, delay)} />
        ))}
      </g>
    </svg>
  );
}

/** A line of ants carrying document chunks across the top of the chat toward Gajju. count = passages found. */
export function AntTrail({ count, mode = "carry" }: { count: number; mode?: "carry" | "rerank" | "retry" | "build" }) {
  const { motionOK, anim } = useApp();
  const n = Math.max(1, Math.min(count, anim === "calm" ? 4 : 8));
  const ants = [...Array(n)].map((_, i) => i);
  if (!motionOK) {
    return <div className="flex gap-1 opacity-80" aria-hidden>{ants.slice(0, 4).map((i) => <Ant key={i} size={20} />)}</div>;
  }
  return (
    <div className="relative h-9 w-full overflow-hidden" aria-hidden>
      <div className="absolute inset-x-0 bottom-1 border-b border-dashed border-ink/15" />
      {ants.map((i) => {
        const dur = anim === "calm" ? 6 : 3.6;
        if (mode === "rerank") {
          // ants shuffle: the best chunks move to the front
          return (
            <motion.div key={i} className="absolute bottom-1" layout
              initial={{ left: `${10 + i * 10}%` }}
              animate={{ left: [`${10 + i * 10}%`, `${10 + ((n - 1 - i) * 10)}%`], y: [0, i % 2 ? -6 : 0, 0] }}
              transition={{ duration: 0.9, ease: "easeInOut" }}>
              <Ant size={24} delay={i * 0.05} />
            </motion.div>
          );
        }
        const back = mode === "retry";
        return (
          <motion.div key={i} className="absolute bottom-1"
            initial={{ left: back ? "92%" : "-8%" }}
            animate={{ left: back ? ["92%", "40%", "60%", "-8%"] : ["-8%", "104%"], y: back ? [0, 0, -8, 0] : 0 }}
            transition={{ duration: back ? dur * 1.2 : dur, repeat: Infinity, delay: i * (dur / n), ease: "linear" }}>
            <Ant size={24} flip={back} delay={i * 0.07} />
          </motion.div>
        );
      })}
    </div>
  );
}

/* ---------------------------------------------------------------- 🦉 owl with magnifier */
export function Owl({ size = 56, looking = true, writing = false }: { size?: number; looking?: boolean; writing?: boolean }) {
  const { motionOK } = useApp();
  return (
    <svg viewBox="0 0 80 80" width={size} height={size} aria-hidden overflow="visible">
      <motion.g animate={motionOK ? { rotate: looking ? [-6, 6, -6] : 0 } : {}} style={{ transformOrigin: "40px 70px", transformBox: "view-box" }} transition={loop(1.6)}>
        <ellipse cx="40" cy="48" rx="24" ry="26" fill="#9a6b43" />
        <ellipse cx="40" cy="54" rx="15" ry="17" fill="#e7c99c" />
        {[48, 55, 62].map((y) => <path key={y} d={`M32 ${y} q4 3 8 0 q4 3 8 0`} stroke="#b88a5a" strokeWidth="1.4" fill="none" />)}
        <path d="M18 26 l6 10 M62 26 l-6 10" stroke="#9a6b43" strokeWidth="6" strokeLinecap="round" />
        <circle cx="30" cy="38" r="10" fill="#fff" /><circle cx="50" cy="38" r="10" fill="#fff" />
        <motion.g animate={motionOK ? { x: looking ? [-2, 2, -2] : 0 } : {}} transition={loop(1.6)}>
          <circle cx="31" cy="38" r="4.6" fill="#1b2a30" /><circle cx="51" cy="38" r="4.6" fill="#1b2a30" />
          <circle cx="32.5" cy="36.5" r="1.4" fill="#fff" /><circle cx="52.5" cy="36.5" r="1.4" fill="#fff" />
        </motion.g>
        <path d="M37 46 l3 5 l3 -5 z" fill="var(--marigold)" />
        <path d="M28 74 l-3 4 M34 75 l0 4 M46 75 l0 4 M52 74 l3 4" stroke="var(--marigold)" strokeWidth="2" strokeLinecap="round" />
      </motion.g>
      {writing ? (
        <g>
          <rect x="54" y="52" width="24" height="18" rx="2" fill="#fff" stroke="var(--line)" />
          <motion.path d="M58 58 h14 M58 63 h10" stroke="var(--peacock)" strokeWidth="1.6" strokeLinecap="round"
            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.2 }} />
        </g>
      ) : (
        <motion.g animate={motionOK && looking ? { x: [-4, 6, -4], y: [0, -3, 0] } : {}} transition={loop(1.6)}>
          <circle cx="66" cy="54" r="9" fill="rgb(255 255 255 / .55)" stroke="#3b4b52" strokeWidth="3" />
          <path d="M72 61 l7 8" stroke="#3b4b52" strokeWidth="4" strokeLinecap="round" />
        </motion.g>
      )}
    </svg>
  );
}

/* ---------------------------------------------------------------- 🦚 peacock fanning feathers */
export function Peacock({ size = 150, play = true }: { size?: number; play?: boolean }) {
  const { motionOK } = useApp();
  const feathers = [...Array(11)].map((_, i) => -75 + i * 15);
  return (
    <svg viewBox="0 0 200 160" width={size} height={size * 0.8} aria-hidden overflow="visible">
      {feathers.map((a, i) => (
        <motion.g key={a} style={{ transformOrigin: "100px 130px", transformBox: "view-box" }}
          initial={motionOK && play ? { rotate: 0, scaleY: 0.2, opacity: 0 } : { rotate: a, opacity: 1 }}
          animate={{ rotate: a, scaleY: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 120, damping: 12, delay: motionOK ? Math.abs(i - 5) * 0.05 : 0 }}>
          <path d="M100 130 L 96 40 Q 100 24 104 40 Z" fill="#1f7a5c" />
          <ellipse cx="100" cy="38" rx="11" ry="14" fill="#2aa37a" />
          <ellipse cx="100" cy="39" rx="7" ry="9" fill="var(--marigold)" />
          <ellipse cx="100" cy="40" rx="4.4" ry="5.6" fill="#0b4f8a" />
        </motion.g>
      ))}
      <ellipse cx="100" cy="128" rx="14" ry="20" fill="#0b5fa8" />
      <path d="M100 112 q-4 -22 4 -30" stroke="#0b5fa8" strokeWidth="9" strokeLinecap="round" fill="none" />
      <circle cx="104" cy="80" r="8" fill="#0b5fa8" />
      <circle cx="106.5" cy="78.5" r="1.8" fill="#fff" />
      <path d="M111 80 l6 2 l-6 2 z" fill="var(--marigold)" />
      {[0, 1, 2].map((i) => <path key={i} d={`M${101 + i * 3} 72 l${-2 + i * 2} -8`} stroke="#0b5fa8" strokeWidth="1.4" />)}
      {[-3, 3, 9].map((x, i) => <circle key={i} cx={98 + x} cy={63 - (i === 1 ? 2 : 0)} r="2" fill="#2aa37a" />)}
    </svg>
  );
}

/* ---------------------------------------------------------------- 🦜 parrot (language detection) */
export function Parrot({ size = 40, talking = true }: { size?: number; talking?: boolean }) {
  const { motionOK } = useApp();
  return (
    <svg viewBox="0 0 60 60" width={size} height={size} aria-hidden overflow="visible">
      <motion.g animate={motionOK ? { rotate: [0, -8, 0] } : {}} style={{ transformOrigin: "30px 50px", transformBox: "view-box" }} transition={loop(0.9)}>
        <path d="M22 52 q-6 4 -4 8 q6 -2 8 -6" fill="#1e9e5a" />
        <ellipse cx="30" cy="36" rx="12" ry="16" fill="#25b868" />
        <path d="M24 34 q-10 6 -6 18 q8 -4 10 -12" fill="#1a8f50" />
        <circle cx="33" cy="20" r="11" fill="#25b868" />
        <circle cx="36" cy="18" r="3" fill="#fff" /><circle cx="36.8" cy="18" r="1.6" fill="#1b2a30" />
        <motion.path d="M42 20 q8 2 4 10 q-3 -4 -6 -4 z" fill="#e85d2b"
          animate={motionOK && talking ? { rotate: [0, 12, 0] } : {}} style={{ transformOrigin: "42px 22px", transformBox: "view-box" }} transition={loop(0.35)} />
        <path d="M26 12 q2 -8 8 -8 q-2 4 -2 8" fill="#e8c21b" />
      </motion.g>
    </svg>
  );
}

/* ---------------------------------------------------------------- 🐿️ squirrel with acorn */
export function Squirrel({ size = 44 }: { size?: number }) {
  return (
    <svg viewBox="0 0 60 60" width={size} height={size} aria-hidden overflow="visible">
      <path d="M14 50 C 0 40, 6 14, 22 18 C 30 20, 26 32, 20 34 C 30 36, 30 50, 14 50 Z" fill="#c9773a" />
      <ellipse cx="34" cy="40" rx="11" ry="12" fill="#d98a48" />
      <circle cx="42" cy="26" r="9" fill="#d98a48" />
      <path d="M38 18 l2 -6 l4 6" fill="#c9773a" />
      <circle cx="45" cy="24" r="1.8" fill="#1b2a30" />
      <ellipse cx="38" cy="44" rx="7" ry="8" fill="#f3d2ae" />
      <g transform="translate(46 34)">
        <ellipse cx="0" cy="4" rx="5" ry="6" fill="#a8672f" />
        <path d="M-6 0 q6 -6 12 0 z" fill="#6f4420" />
      </g>
    </svg>
  );
}

/* ---------------------------------------------------------------- 🐢 tortoise (slow network) */
export function Tortoise({ size = 64 }: { size?: number }) {
  const { motionOK } = useApp();
  return (
    <svg viewBox="0 0 90 50" width={size} height={size * 0.56} aria-hidden overflow="visible">
      <motion.g animate={motionOK ? { y: [0, -1.5, 0] } : {}} transition={loop(0.8)}>
        <motion.path d="M70 30 q12 -2 14 -10 q-8 -4 -14 4" fill="#7fa35a"
          animate={motionOK ? { rotate: [-4, 4, -4] } : {}} style={{ transformOrigin: "70px 28px", transformBox: "view-box" }} transition={loop(1.2)} />
        <circle cx="82" cy="20" r="1.4" fill="#1b2a30" />
        <path d="M14 34 Q 14 6 44 6 Q 74 6 74 34 Z" fill="#5c8a3a" />
        <path d="M24 30 L 32 14 L 44 12 L 56 14 L 64 30 M32 14 L 38 30 M56 14 L 50 30 M44 12 L 44 30" stroke="#3f6526" strokeWidth="2" fill="none" />
        <rect x="10" y="32" width="68" height="5" rx="2.5" fill="#3f6526" />
      </motion.g>
      {[22, 34, 54, 66].map((x, i) => (
        <motion.rect key={x} x={x} y="36" width="8" height="10" rx="4" fill="#7fa35a"
          animate={motionOK ? { rotate: i % 2 ? [-15, 15, -15] : [15, -15, 15] } : {}}
          style={{ transformOrigin: `${x + 4}px 36px`, transformBox: "view-box" }} transition={loop(0.8)} />
      ))}
    </svg>
  );
}

/* ---------------------------------------------------------------- 🦋 butterfly */
export function Butterfly({ size = 30 }: { size?: number }) {
  const { motionOK } = useApp();
  return (
    <svg viewBox="0 0 40 30" width={size} height={size * 0.75} aria-hidden overflow="visible">
      <motion.g animate={motionOK ? { scaleX: [1, 0.3, 1] } : {}} style={{ transformOrigin: "20px 15px", transformBox: "view-box" }} transition={loop(0.28)}>
        <path d="M20 15 C 6 0, -2 10, 8 16 C -2 22, 8 30, 20 17 Z" fill="var(--marigold)" />
        <path d="M20 15 C 34 0, 42 10, 32 16 C 42 22, 32 30, 20 17 Z" fill="#e8731b" />
        <circle cx="10" cy="11" r="2" fill="#fff" opacity=".8" /><circle cx="30" cy="11" r="2" fill="#fff" opacity=".8" />
      </motion.g>
      <rect x="19" y="9" width="2" height="14" rx="1" fill="#3b2417" />
    </svg>
  );
}

/* ---------------------------------------------------------------- 🐝 bee */
export function Bee({ size = 22 }: { size?: number }) {
  const { motionOK } = useApp();
  return (
    <svg viewBox="0 0 30 24" width={size} height={size * 0.8} aria-hidden overflow="visible">
      <motion.g animate={motionOK ? { scaleY: [1, 0.4, 1] } : {}} style={{ transformOrigin: "14px 9px", transformBox: "view-box" }} transition={loop(0.12)}>
        <ellipse cx="10" cy="6" rx="6" ry="4.5" fill="#dff3ff" opacity=".9" />
        <ellipse cx="18" cy="6" rx="6" ry="4.5" fill="#dff3ff" opacity=".9" />
      </motion.g>
      <ellipse cx="14" cy="14" rx="10" ry="7" fill="#f4c21b" />
      <path d="M10 8 v12 M16 7.5 v13" stroke="#2b2b2b" strokeWidth="2.6" />
      <circle cx="22" cy="12" r="1.4" fill="#2b2b2b" />
      <path d="M3 14 l-3 1" stroke="#2b2b2b" strokeWidth="1.6" />
    </svg>
  );
}

/* ---------------------------------------------------------------- 🦎 chameleon (freshness warning) */
export function Chameleon({ size = 40 }: { size?: number }) {
  const { motionOK } = useApp();
  return (
    <svg viewBox="0 0 60 36" width={size} height={size * 0.6} aria-hidden overflow="visible">
      <motion.g animate={motionOK ? { fill: ["#4caf50", "#f4a51c", "#0b6e84", "#4caf50"] } : { fill: "#4caf50" }} transition={loop(3.6)}>
        <path d="M8 20 C 8 8, 30 4, 40 12 C 46 16, 48 22, 42 26 C 34 30, 14 30, 8 20 Z" />
        <path d="M40 12 C 50 8, 58 14, 54 20 C 52 24, 46 22, 44 20" />
        <path d="M8 22 C 0 24, 0 34, 8 32 C 12 31, 12 26, 8 27" fill="none" stroke="currentColor" strokeWidth="3" />
      </motion.g>
      <circle cx="50" cy="15" r="3.6" fill="#fff" /><circle cx="51" cy="15" r="1.8" fill="#1b2a30" />
      <path d="M18 28 l-2 6 M30 28 l2 6" stroke="#3f6526" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  );
}

/* ---------------------------------------------------------------- 🐒 monkey on a vine (pull to refresh) */
export function Monkey({ progress = 1, size = 52 }: { progress?: number; size?: number }) {
  return (
    <svg viewBox="0 0 60 90" width={size} height={size * 1.5} aria-hidden overflow="visible">
      <path d={`M30 0 Q ${30 + 8 * (1 - progress)} ${20 * progress} 30 ${34 * progress + 6}`} stroke="#4f7a32" strokeWidth="3" fill="none" />
      <g transform={`translate(0 ${34 * progress})`}>
        <path d="M30 6 l0 6" stroke="#8a5a34" strokeWidth="4" strokeLinecap="round" />
        <circle cx="30" cy="26" r="13" fill="#8a5a34" />
        <ellipse cx="30" cy="29" rx="9" ry="8" fill="#e6c09a" />
        <circle cx="17" cy="22" r="5" fill="#8a5a34" /><circle cx="43" cy="22" r="5" fill="#8a5a34" />
        <circle cx="26" cy="25" r="1.8" fill="#1b2a30" /><circle cx="34" cy="25" r="1.8" fill="#1b2a30" />
        <path d="M26 32 q4 3 8 0" stroke="#1b2a30" strokeWidth="1.6" fill="none" strokeLinecap="round" />
        <ellipse cx="30" cy="48" rx="10" ry="11" fill="#8a5a34" />
        <path d="M40 52 q12 4 8 16" stroke="#8a5a34" strokeWidth="3" fill="none" strokeLinecap="round" />
      </g>
    </svg>
  );
}

/* ---------------------------------------------------------------- 🌙 fireflies (offline mode) */
export function Fireflies({ count = 12 }: { count?: number }) {
  const { motionOK } = useApp();
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      {[...Array(count)].map((_, i) => {
        const left = (i * 37) % 100, top = (i * 53) % 100;
        return (
          <motion.span key={i} className="absolute h-1.5 w-1.5 rounded-full bg-[#ffe27a] shadow-[0_0_10px_4px_rgba(255,226,122,.55)]"
            style={{ left: `${left}%`, top: `${top}%` }}
            animate={motionOK ? { opacity: [0.15, 1, 0.15], x: [0, (i % 2 ? 14 : -14), 0], y: [0, -10, 0] } : { opacity: 0.7 }}
            transition={motionOK ? { duration: 2.6 + (i % 4) * 0.6, repeat: Infinity, delay: i * 0.3 } : {}} />
        );
      })}
    </div>
  );
}

/* ---------------------------------------------------------------- 🐦 bird + 🌳 tree (empty state) */
export function Bird({ size = 22 }: { size?: number }) {
  const { motionOK } = useApp();
  return (
    <svg viewBox="0 0 30 24" width={size} height={size * 0.8} aria-hidden overflow="visible">
      <motion.g animate={motionOK ? { rotate: [0, -10, 0, 6, 0] } : {}} style={{ transformOrigin: "15px 20px", transformBox: "view-box" }} transition={loop(2.4)}>
        <ellipse cx="14" cy="15" rx="9" ry="7" fill="#e8731b" />
        <circle cx="21" cy="10" r="5" fill="#e8731b" />
        <circle cx="22.5" cy="9" r="1.2" fill="#1b2a30" />
        <path d="M26 10 l4 1 l-4 1.6 z" fill="var(--marigold)" />
        <path d="M8 13 q-6 -2 -7 3 q5 1 8 -1" fill="#c75a12" />
      </motion.g>
    </svg>
  );
}

export function Tree({ className = "" }: { className?: string }) {
  const { motionOK } = useApp();
  return (
    <svg viewBox="0 0 220 200" className={className} aria-hidden>
      <path d="M104 200 C 106 160, 100 130, 108 100 L 120 100 C 124 130, 118 160, 124 200 Z" fill="#8a5a34" />
      <path d="M112 128 q-24 -10 -34 -30 M116 118 q22 -8 30 -26" stroke="#8a5a34" strokeWidth="6" strokeLinecap="round" fill="none" />
      <motion.g animate={motionOK ? { rotate: [-1, 1, -1] } : {}} style={{ transformOrigin: "112px 110px", transformBox: "view-box" }} transition={loop(5)}>
        <circle cx="70" cy="80" r="40" fill="#3f8f4f" />
        <circle cx="150" cy="76" r="42" fill="#3f8f4f" />
        <circle cx="110" cy="46" r="46" fill="#4aa35b" />
        <circle cx="96" cy="34" r="14" fill="#fff" opacity=".08" />
        {[[60, 70], [150, 60], [118, 30], [92, 92], [170, 96]].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="5" fill="var(--marigold)" />
        ))}
      </motion.g>
    </svg>
  );
}
