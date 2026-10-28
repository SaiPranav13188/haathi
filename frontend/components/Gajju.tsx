"use client";

/**
 * Gajju the baby elephant (haathi.md §9.2). Placeholder for the Rive state machine with the same API:
 * a hand-built SVG animated with Motion. States: idle, wave, listening, thinking, asking, found, unsure,
 * not_eligible, error, language_switch, celebrate (+ nod / hop micro-reactions).
 * With Reduce Motion or Animation = Off it renders a static pose for the state.
 */
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useState } from "react";
import { useApp } from "@/lib/app-context";

export type GajjuState =
  | "idle" | "wave" | "listening" | "thinking" | "asking" | "found" | "unsure" | "not_eligible" | "error"
  | "language_switch" | "celebrate" | "nod" | "hop" | "tilt";

const LABELS: Record<GajjuState, string> = {
  idle: "Gajju the elephant is resting", wave: "Gajju waves hello", listening: "Gajju is listening",
  thinking: "Gajju is reading the documents", asking: "Gajju is asking a question", found: "Gajju found schemes for you",
  unsure: "Gajju is not sure and suggests the official portal", not_eligible: "Gajju gently comforts you",
  error: "Gajju fell asleep: connection problem", language_switch: "Gajju changed language", celebrate: "Gajju celebrates",
  nod: "Gajju nods", hop: "Gajju hops happily", tilt: "Gajju tilts his head",
};

const CAP: Record<string, string> = { en: "A", hi: "अ", te: "అ" };

export default function Gajju({ state = "idle", size = 120, voiceLevel = 0, className = "", decorative = false }: {
  state?: GajjuState; size?: number; voiceLevel?: number; className?: string; decorative?: boolean;
}) {
  const { motionOK, anim, lang } = useApp();
  const live = motionOK;
  const calm = anim === "calm";
  const uid = useId().replace(/:/g, "");
  const [blink, setBlink] = useState(false);

  useEffect(() => {
    if (!live || state === "error") return;
    let t: ReturnType<typeof setTimeout>;
    const loop = () => {
      t = setTimeout(() => { setBlink(true); setTimeout(() => setBlink(false), 140); loop(); }, 2600 + Math.random() * 2800);
    };
    loop();
    return () => clearTimeout(t);
  }, [live, state]);

  const rep = (d: number) => (live ? { duration: d, repeat: Infinity, ease: "easeInOut" as const } : { duration: 0 });
  const once = (d: number) => (live ? { duration: d, ease: "easeInOut" as const } : { duration: 0 });

  // ---------- per-state poses ----------
  const ears = {
    idle: { l: live ? { rotate: [-3, 4, -3] } : { rotate: 0 }, r: live ? { rotate: [3, -4, 3] } : { rotate: 0 }, tr: rep(calm ? 5 : 3.4) },
    listening: { l: { rotate: -16, scale: 1.14 }, r: { rotate: 16, scale: 1.14 }, tr: once(0.3) },
    found: { l: live ? { rotate: [-4, -18, -4] } : { rotate: -10 }, r: live ? { rotate: [4, 18, 4] } : { rotate: 10 }, tr: rep(0.45) },
    unsure: { l: { rotate: -10, y: -4 }, r: { rotate: 10, y: -4 }, tr: once(0.35) },
    error: { l: { rotate: 8, y: 4 }, r: { rotate: -8, y: 4 }, tr: once(0.6) },
  } as const;
  const earPose = ears[(state in ears ? state : "idle") as keyof typeof ears];

  const headPose =
    state === "asking" || state === "tilt" ? { rotate: 9 } :
    state === "nod" ? (live ? { rotate: [0, 7, 0, 5, 0] } : { rotate: 0 }) :
    state === "not_eligible" ? (live ? { rotate: [0, -5, 0] } : { rotate: -4 }) :
    state === "error" ? { rotate: -8, y: 4 } :
    { rotate: 0, y: 0 };

  const trunkPose =
    state === "wave" ? (live ? { rotate: [0, -38, -18, -38, -18, 0] } : { rotate: -30 }) :
    state === "thinking" ? (live ? { rotate: [-4, 10, -4] } : { rotate: 4 }) :
    state === "unsure" ? { rotate: -28 } :
    state === "found" || state === "celebrate" ? (live ? { rotate: [0, -40, -30] } : { rotate: -35 }) :
    state === "not_eligible" ? (live ? { rotate: [0, -16, -8, -16, 0] } : { rotate: -10 }) :
    state === "listening" ? { rotate: -6 } :
    live ? { rotate: [-2, 3, -2] } : { rotate: 0 };
  const trunkTr = state === "wave" || state === "not_eligible" ? once(1.3) : state === "thinking" ? rep(0.9) :
    state === "found" || state === "celebrate" ? once(0.6) : state === "idle" ? rep(calm ? 5 : 3.2) : once(0.4);

  const wholePose =
    state === "found" || state === "hop" ? (live ? { y: [0, -14, 0, -8, 0] } : { y: 0 }) :
    state === "celebrate" ? (live ? { rotate: [0, 360], y: [0, -10, 0] } : { rotate: 0 }) :
    state === "language_switch" ? (live ? { scaleX: [1, -1, -1, 1] } : { scaleX: 1 }) :
    { y: 0, rotate: 0, scaleX: 1 };
  const wholeTr = state === "celebrate" ? once(0.9) : state === "language_switch" ? once(0.9) : once(0.8);

  const eyesClosed = state === "error";
  const happy = state === "found" || state === "celebrate" || state === "hop";
  const ring = 1 + Math.min(1, voiceLevel) * 0.9;

  return (
    <div className={`relative inline-block select-none ${className}`} style={{ width: size, height: size }}
         role={decorative ? undefined : "img"} aria-hidden={decorative || undefined} aria-label={decorative ? undefined : LABELS[state]}>
      <svg viewBox="0 0 200 200" width={size} height={size} overflow="visible">
        <defs>
          <radialGradient id={`h${uid}`} cx="42%" cy="34%" r="70%">
            <stop offset="0%" stopColor="var(--elephant-light)" />
            <stop offset="100%" stopColor="var(--elephant)" />
          </radialGradient>
          <radialGradient id={`e${uid}`} cx="50%" cy="50%" r="60%">
            <stop offset="0%" stopColor="#f7c3cc" />
            <stop offset="100%" stopColor="#ee9fae" />
          </radialGradient>
        </defs>

        {/* ground shadow */}
        <motion.ellipse cx="100" cy="190" rx="44" ry="6" fill="currentColor" className="text-ink/10"
          style={{ transformOrigin: "100px 190px", transformBox: "view-box" }}
          animate={(state === "found" || state === "hop") && live ? { scaleX: [1, 0.7, 1, 0.82, 1] } : { scaleX: 1 }} transition={wholeTr} />

        <motion.g style={{ transformOrigin: "100px 120px", transformBox: "view-box" }} animate={wholePose} transition={wholeTr}>
          {/* listening rings from the ears */}
          <AnimatePresence>
            {state === "listening" && [0, 1, 2].map((i) => (
              <motion.g key={i}>
                {[38, 162].map((cx) => (
                  <motion.circle key={cx} cx={cx} cy="82" r="22" fill="none" stroke="var(--peacock)" strokeWidth="2.5"
                    initial={{ opacity: 0, scale: 0.6 }} style={{ transformOrigin: `${cx}px 82px`, transformBox: "view-box" }}
                    animate={live ? { opacity: [0.7, 0], scale: [0.8, 1.5 * ring] } : { opacity: 0.4, scale: 1.1 }}
                    exit={{ opacity: 0 }} transition={live ? { duration: 1.4, repeat: Infinity, delay: i * 0.45 } : { duration: 0 }} />
                ))}
              </motion.g>
            ))}
          </AnimatePresence>

          {/* body */}
          <motion.g style={{ transformOrigin: "100px 190px", transformBox: "view-box" }}
            animate={live ? { scaleY: [1, 1.02, 1] } : { scaleY: 1 }} transition={rep(calm ? 5 : 3.6)}>
            <ellipse cx="100" cy="160" rx="46" ry="32" fill="var(--elephant)" />
            <rect x="66" y="168" width="22" height="22" rx="10" fill="var(--elephant-dark)" />
            <rect x="112" y="168" width="22" height="22" rx="10" fill="var(--elephant-dark)" />
            <path d="M70 186 h14 M116 186 h14" stroke="#f4efe6" strokeWidth="2.5" strokeLinecap="round" opacity=".7" />
          </motion.g>

          {/* head group */}
          <motion.g style={{ transformOrigin: "100px 130px", transformBox: "view-box" }} animate={headPose}
            transition={state === "nod" ? once(0.7) : once(0.45)}>
            {/* ears */}
            <motion.g style={{ transformOrigin: "74px 78px", transformBox: "view-box" }} animate={earPose.l} transition={earPose.tr}>
              <path d="M74 52 C 40 36, 10 60, 16 96 C 21 124, 48 134, 70 118 Z" fill="var(--elephant-dark)" />
              <path d="M68 62 C 44 52, 26 70, 30 94 C 33 112, 50 118, 64 110 Z" fill={`url(#e${uid})`} opacity=".85" />
            </motion.g>
            <motion.g style={{ transformOrigin: "126px 78px", transformBox: "view-box" }} animate={earPose.r} transition={earPose.tr}>
              <path d="M126 52 C 160 36, 190 60, 184 96 C 179 124, 152 134, 130 118 Z" fill="var(--elephant-dark)" />
              <path d="M132 62 C 156 52, 174 70, 170 94 C 167 112, 150 118, 136 110 Z" fill={`url(#e${uid})`} opacity=".85" />
            </motion.g>

            {/* head */}
            <circle cx="100" cy="86" r="48" fill={`url(#h${uid})`} />
            <ellipse cx="86" cy="58" rx="20" ry="10" fill="#fff" opacity=".18" />
            {/* marigold tuft (brand accent) */}
            <g transform="translate(100 38)">
              {[0, 72, 144, 216, 288].map((a) => (
                <ellipse key={a} cx="0" cy="-6" rx="4" ry="6" fill="var(--marigold)" transform={`rotate(${a})`} />
              ))}
              <circle r="3.2" fill="#d9820a" />
            </g>

            {/* cheeks */}
            <circle cx="72" cy="104" r="8" fill="#f39aab" opacity={happy ? 0.75 : 0.45} />
            <circle cx="128" cy="104" r="8" fill="#f39aab" opacity={happy ? 0.75 : 0.45} />

            {/* brows */}
            {(state === "asking" || state === "unsure" || state === "not_eligible") && (
              <g stroke="var(--elephant-dark)" strokeWidth="3" strokeLinecap="round">
                <path d={state === "asking" ? "M72 70 q8 -6 16 -2" : "M72 72 q8 -4 16 0"} />
                <path d={state === "asking" ? "M112 66 q8 -2 16 4" : "M112 72 q8 -4 16 0"} />
              </g>
            )}

            {/* eyes */}
            {eyesClosed ? (
              <g stroke="#1b2a30" strokeWidth="3" strokeLinecap="round" fill="none">
                <path d="M74 88 q7 5 14 0" /><path d="M112 88 q7 5 14 0" />
              </g>
            ) : happy ? (
              <g stroke="#1b2a30" strokeWidth="3.4" strokeLinecap="round" fill="none">
                <path d="M74 90 q7 -9 14 0" /><path d="M112 90 q7 -9 14 0" />
              </g>
            ) : (
              <motion.g style={{ transformOrigin: "100px 86px", transformBox: "view-box" }}
                animate={{ scaleY: blink ? 0.1 : 1 }} transition={{ duration: 0.08 }}>
                <ellipse cx="81" cy="86" rx="6" ry="7.5" fill="#1b2a30" />
                <ellipse cx="119" cy="86" rx="6" ry="7.5" fill="#1b2a30" />
                <circle cx="83" cy="83" r="2.2" fill="#fff" /><circle cx="121" cy="83" r="2.2" fill="#fff" />
              </motion.g>
            )}

            {/* glasses while reading */}
            <AnimatePresence>
              {state === "thinking" && (
                <motion.g initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                  stroke="#1b2a30" strokeWidth="2.6" fill="rgb(255 255 255 / .25)">
                  <circle cx="81" cy="86" r="11" /><circle cx="119" cy="86" r="11" /><path d="M92 85 q8 -5 16 0" fill="none" />
                </motion.g>
              )}
            </AnimatePresence>

            {/* smile */}
            <path d={happy ? "M84 112 q6 9 13 4" : state === "error" ? "M86 114 q5 2 10 0" : "M85 112 q5 6 11 3"}
              stroke="#1b2a30" strokeWidth="2.6" fill="none" strokeLinecap="round" />

            {/* trunk */}
            <motion.g style={{ transformOrigin: "100px 104px", transformBox: "view-box" }} animate={trunkPose} transition={trunkTr}>
              <path d="M91 100 C 89 122, 92 140, 100 150 C 106 158, 119 158, 123 149 C 125 144, 121 140, 116 143 C 111 147, 106 144, 106 136 C 106 124, 108 112, 109 100 Z"
                fill={`url(#h${uid})`} stroke="var(--elephant-dark)" strokeWidth="1.6" strokeLinejoin="round" />
              <g stroke="var(--elephant-dark)" strokeWidth="1.8" strokeLinecap="round" opacity=".55" fill="none">
                <path d="M93 116 q7 3 14 0" /><path d="M94 126 q6 3 12 0" /><path d="M96 136 q5 2 10 0" />
              </g>
              {/* sparkle fountain from the trunk */}
              <AnimatePresence>
                {state === "celebrate" && live && [...Array(10)].map((_, i) => (
                  <motion.circle key={i} cx="120" cy="148" r={2 + (i % 3)} fill={i % 2 ? "var(--marigold)" : "var(--peacock)"}
                    initial={{ opacity: 1, x: 0, y: 0 }}
                    animate={{ opacity: [1, 1, 0], x: (i - 5) * 9, y: [-10, -70 - (i % 4) * 12, -40] }}
                    transition={{ duration: 1.1, delay: i * 0.04 }} />
                ))}
              </AnimatePresence>
            </motion.g>

            {/* language cap */}
            <AnimatePresence>
              {state === "language_switch" && (
                <motion.g initial={{ y: -30, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -20, opacity: 0 }}
                  transition={{ delay: live ? 0.45 : 0, type: "spring", stiffness: 300, damping: 16 }}>
                  <path d="M66 48 Q 100 12 134 48 Z" fill="var(--peacock)" />
                  <rect x="60" y="44" width="80" height="9" rx="4.5" fill="var(--peacock-deep)" />
                  <text x="100" y="42" textAnchor="middle" fontSize="20" fontWeight="700" fill="#fff">{CAP[lang]}</text>
                </motion.g>
              )}
            </AnimatePresence>
          </motion.g>

          {/* papers being flipped */}
          <AnimatePresence>
            {state === "thinking" && (
              <motion.g initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <rect x="118" y="150" width="46" height="34" rx="3" fill="#fff" stroke="var(--line)" transform="rotate(-6 141 167)" />
                <rect x="120" y="148" width="46" height="34" rx="3" fill="#fffaf0" stroke="var(--line)" />
                {[156, 162, 168, 174].map((y) => <rect key={y} x="126" y={y} width={y === 174 ? 20 : 32} height="2.4" rx="1.2" fill="var(--ink-3)" opacity=".5" />)}
                <motion.rect x="143" y="148" width="23" height="34" rx="2" fill="#fff" stroke="var(--line)"
                  style={{ transformOrigin: "143px 165px", transformBox: "view-box" }}
                  animate={live ? { scaleX: [1, -1, 1] } : {}} transition={live ? { duration: 1.2, repeat: Infinity, repeatDelay: 0.3 } : {}} />
              </motion.g>
            )}
          </AnimatePresence>
        </motion.g>

        {/* question bubble */}
        <AnimatePresence>
          {state === "asking" && (
            <motion.g initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0, opacity: 0 }}
              style={{ transformOrigin: "164px 34px", transformBox: "view-box" }} transition={{ type: "spring", stiffness: 500, damping: 15 }}>
              <circle cx="164" cy="34" r="20" fill="var(--marigold)" />
              <circle cx="148" cy="56" r="5" fill="var(--marigold)" />
              <text x="164" y="42" textAnchor="middle" fontSize="24" fontWeight="800" fill="#1b2a30">?</text>
            </motion.g>
          )}
        </AnimatePresence>

        {/* unsure: points at the official portal sign */}
        <AnimatePresence>
          {state === "unsure" && (
            <motion.g initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
              <rect x="150" y="118" width="46" height="26" rx="6" fill="var(--peacock)" />
              <text x="173" y="136" textAnchor="middle" fontSize="15" fill="#fff" fontWeight="700">i</text>
              <rect x="171" y="144" width="4" height="22" fill="var(--peacock-deep)" />
            </motion.g>
          )}
        </AnimatePresence>

        {/* comforting heart */}
        <AnimatePresence>
          {state === "not_eligible" && (
            <motion.path d="M150 60 c -6 -8 -18 -2 -12 8 l 12 12 l 12 -12 c 6 -10 -6 -16 -12 -8 z" fill="var(--coral)"
              initial={{ opacity: 0, y: 10, scale: 0.6 }} animate={live ? { opacity: [0, 1, 0.9], y: [10, -4, -2], scale: 1 } : { opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }} transition={{ duration: 1.2 }} style={{ transformOrigin: "150px 70px", transformBox: "view-box" }} />
          )}
        </AnimatePresence>

        {/* sleeping Zzz */}
        <AnimatePresence>
          {state === "error" && ["Z", "z", "z"].map((z, i) => (
            <motion.text key={i} x={150 + i * 12} y={58 - i * 14} fontSize={22 - i * 4} fontWeight="800" fill="var(--peacock)"
              initial={{ opacity: 0 }} animate={live ? { opacity: [0, 1, 0], y: [0, -14] } : { opacity: 0.9 }} exit={{ opacity: 0 }}
              transition={live ? { duration: 2.2, repeat: Infinity, delay: i * 0.5 } : {}}>{z}</motion.text>
          ))}
        </AnimatePresence>

        {/* marigold petal confetti */}
        <AnimatePresence>
          {state === "found" && live && [...Array(14)].map((_, i) => {
            const a = (i / 14) * Math.PI * 2;
            return (
              <motion.ellipse key={i} cx="100" cy="50" rx="3.4" ry="6" fill={i % 3 ? "var(--marigold)" : "#e8731b"}
                initial={{ opacity: 1, x: 0, y: 0, rotate: 0 }}
                animate={{ opacity: [1, 1, 0], x: Math.cos(a) * 80, y: [Math.sin(a) * 40 - 30, Math.sin(a) * 60 + 50], rotate: 360 }}
                transition={{ duration: 1.5, ease: "easeOut" }} />
            );
          })}
        </AnimatePresence>
      </svg>
    </div>
  );
}
