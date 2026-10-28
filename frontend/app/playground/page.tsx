"use client";

import { useState } from "react";
import { useApp } from "@/lib/app-context";
import Gajju, { type GajjuState } from "@/components/Gajju";
import MicButton from "@/components/MicButton";
import { AntTrail, Bee, Bird, Butterfly, Chameleon, Fireflies, Monkey, Owl, Parrot, Peacock, Squirrel, Tortoise, Tree } from "@/components/animals";
import { Button, CountUp, Segmented } from "@/components/ui";
import type { AnimLevel } from "@/lib/types";

const STATES: GajjuState[] = ["idle", "wave", "listening", "thinking", "asking", "found", "unsure", "not_eligible", "error", "language_switch", "celebrate", "nod", "hop"];

/** Preview every Gajju state and animal animation (Prompt 7). */
export default function Playground() {
  const { anim, setAnim, toast } = useApp();
  const [st, setSt] = useState<GajjuState>("idle");
  const [level, setLevel] = useState(0.4);
  const [k, setK] = useState(0);
  const tile = "flex flex-col items-center justify-center gap-2 rounded-3xl border border-line bg-surface p-4 text-center text-sm font-semibold shadow-card";
  return (
    <div className="mx-auto max-w-5xl px-4 pb-16 pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold">Animation playground</h1>
        <Segmented<AnimLevel> label="Animation level" value={anim} onChange={setAnim} options={[{ value: "full", label: "Full" }, { value: "calm", label: "Calm" }, { value: "off", label: "Off" }]} />
      </div>
      <section className="mt-4 grid gap-4 rounded-3xl border border-line bg-surface p-5 md:grid-cols-[260px_1fr]">
        <div className="grid place-items-center"><Gajju key={`${st}-${k}`} state={st} size={220} voiceLevel={level} /></div>
        <div>
          <p className="mb-2 font-bold">Gajju states (Rive state-machine API: isListening, stage, result, voiceLevel)</p>
          <div className="flex flex-wrap gap-2">
            {STATES.map((s) => <Button key={s} size="sm" variant={s === st ? "primary" : "secondary"} onClick={() => { setSt(s); setK((x) => x + 1); }}>{s}</Button>)}
          </div>
          <label className="mt-4 block text-sm font-semibold">voiceLevel {level.toFixed(2)}
            <input type="range" min={0} max={1} step={0.01} value={level} onChange={(e) => setLevel(Number(e.target.value))} className="mt-1 w-full accent-[var(--peacock)]" />
          </label>
        </div>
      </section>
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className={`${tile} col-span-2`}><AntTrail key={`a${k}`} count={6} />1–3 · Ants: retrieval / rerank / retry</div>
        <div className={tile}><AntTrail key={`r${k}`} count={5} mode="rerank" />Rerank</div>
        <div className={tile}><AntTrail key={`b${k}`} count={4} mode="retry" />Retry</div>
        <div className={tile}><Owl size={80} />4 · Owl verifying</div>
        <div className={tile}><Peacock key={`p${k}`} size={150} />5 · Peacock reveal</div>
        <div className={tile}><Parrot size={64} />6 · Parrot: language</div>
        <div className={tile}><Squirrel size={64} />7 · Squirrel: save</div>
        <div className={tile}><Tortoise size={90} />8 · Tortoise: slow network</div>
        <div className={tile}><Gajju state="nod" size={80} />9 · Checklist nod</div>
        <div className={tile}><Butterfly size={56} />10 · Butterfly: what-if</div>
        <div className={tile}><Bee size={44} />11 · Bees: documents</div>
        <div className={tile}><Chameleon size={70} />12 · Chameleon: rule changed</div>
        <div className={tile}><div className="relative h-24 w-32"><Tree className="h-full w-full" /><div className="absolute left-[60px] top-6"><Bird /></div></div>13 · Empty state</div>
        <div className={tile}><div className="flex"><Gajju size={50} decorative /><Peacock size={60} play={false} /><Owl size={50} /></div>14 · Onboarding helpers</div>
        <div className={tile}><MicButton listening level={level} onClick={() => {}} />15 · Mic ear</div>
        <div className={tile}><Monkey progress={level} size={40} />16 · Monkey: pull</div>
        <div className={tile}><Gajju state="hop" size={70} key={`h${k}`} />17 · Thumbs up</div>
        <div className={tile}><Owl size={70} writing />18 · Thumbs down</div>
        <div className={tile}><div className="w-full space-y-1.5">{[90, 70, 80].map((w) => <div key={w} className="shimmer h-3 rounded-full" style={{ width: `${w}%` }} />)}</div>19 · Skeleton</div>
        <div className={`${tile} relative overflow-hidden bg-[#0d1b2a] text-[#f6efd9]`}><Fireflies count={10} />20 · Fireflies: offline</div>
        <div className={tile}><span className="text-2xl font-extrabold text-peacock"><CountUp key={k} value={12000} /></span>Benefit count-up</div>
        <div className={tile}><Button onClick={() => toast("Saved for offline use", "ok", "🐿️")}>Toast</Button>Toast + progress bar</div>
      </div>
    </div>
  );
}
