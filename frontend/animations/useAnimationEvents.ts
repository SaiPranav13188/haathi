"use client";

/**
 * Maps backend SSE events (haathi.md §9.5) to Gajju states and animal animations.
 *
 * Events arrive as fast as the pipeline runs (often < 100 ms). Text is never held back; only the *stage
 * display* is paced (MIN_STAGE_MS each) so people can see what the system is doing, like ants carrying
 * passages, then the owl checking citations.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { GajjuState } from "@/components/Gajju";
import type { StreamEvent } from "@/lib/types";

export type Phase = "idle" | "understand" | "retrieve" | "rerank" | "retry" | "eligibility" | "ask" | "verify" | "writing" | "done" | "error";

export interface AnimState {
  phase: Phase;
  passages: number;
  retries: number;
  verify: Record<number, string>;
  result: string | null;
  detected: { lang: string; script: string; code_mixed: boolean; romanized: boolean } | null;
  slow: boolean;
}

const INITIAL: AnimState = { phase: "idle", passages: 0, retries: 0, verify: {}, result: null, detected: null, slow: false };
const MIN_STAGE_MS = { understand: 350, retrieve: 900, rerank: 650, retry: 900, eligibility: 450, ask: 300, verify: 900, writing: 200 } as const;

export function gajjuFor(a: AnimState, listening: boolean): GajjuState {
  if (listening) return "listening";
  switch (a.phase) {
    case "understand": case "retrieve": case "rerank": case "retry": case "eligibility": case "verify": case "writing":
      return "thinking";
    case "error":
      return "error";
    case "done":
      return a.result === "eligible" ? "found" : a.result === "unsure" ? "unsure" : a.result === "not_eligible" ? "not_eligible"
        : a.result === "asking" ? "asking" : "idle";
    default:
      return "idle";
  }
}

export function useAnimationEvents(fast: boolean) {
  const [state, setState] = useState<AnimState>(INITIAL);
  const queue = useRef<Array<(s: AnimState) => AnimState>>([]);
  const busy = useRef(false);
  const cur = useRef<AnimState>(INITIAL);
  const slowTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const pump = useCallback(() => {
    if (busy.current) return;
    const next = queue.current.shift();
    if (!next) return;
    busy.current = true;
    const n = next(cur.current);
    const changed = n.phase !== cur.current.phase;
    cur.current = n;
    setState(n);
    const wait = fast || !changed ? 0 : (MIN_STAGE_MS as Record<string, number>)[n.phase] ?? 0;
    setTimeout(() => { busy.current = false; pump(); }, wait);
  }, [fast]);

  const push = useCallback((fn: (s: AnimState) => AnimState) => { queue.current.push(fn); pump(); }, [pump]);

  const begin = useCallback(() => {
    queue.current = [];
    busy.current = false;
    cur.current = { ...INITIAL, phase: "understand" };
    setState(cur.current);
    if (slowTimer.current) clearTimeout(slowTimer.current);
    // 🐢 after 3 s with no answer, the tortoise walks across
    slowTimer.current = setTimeout(() => {
      if (cur.current.phase !== "done" && cur.current.phase !== "error") { cur.current = { ...cur.current, slow: true }; setState(cur.current); }
    }, 3000);
  }, []);

  const onEvent = useCallback((e: StreamEvent) => {
    if (e.type === "stage") {
      const st = e.stage;
      if (st === "understand") {
        push((s) => ({ ...s, phase: "understand", detected: { lang: String(e.lang), script: String(e.script), code_mixed: !!e.code_mixed, romanized: !!e.romanized } }));
      } else if (st === "retrieve") {
        push((s) => ({ ...s, phase: s.retries ? "retry" : "retrieve", passages: Number(e.count ?? 0) }));
      } else if (st === "rerank") {
        push((s) => ({ ...s, phase: "rerank" }));
      } else if (st === "retry") {
        push((s) => ({ ...s, phase: "retry", retries: s.retries + 1 }));
      } else if (st === "eligibility") {
        push((s) => ({ ...s, phase: "eligibility" }));
      } else if (st === "ask") {
        push((s) => ({ ...s, phase: "ask" }));
      } else if (st === "verify") {
        const id = Number(e.citation_id);
        push((s) => ({ ...s, phase: "verify", verify: { ...s.verify, [id]: String(e.status) } }));
      } else if (st === "generate") {
        push((s) => ({ ...s, phase: "writing" }));
      }
    } else if (e.type === "result") {
      push((s) => ({ ...s, result: e.kind }));
    } else if (e.type === "done") {
      push((s) => ({ ...s, phase: "done", slow: false }));
      if (slowTimer.current) clearTimeout(slowTimer.current);
    } else if (e.type === "error") {
      queue.current = [];
      cur.current = { ...cur.current, phase: "error", slow: false };
      setState(cur.current);
      if (slowTimer.current) clearTimeout(slowTimer.current);
    }
  }, [push]);

  const fail = useCallback(() => {
    queue.current = [];
    if (slowTimer.current) clearTimeout(slowTimer.current);
    cur.current = { ...cur.current, phase: "error", slow: false };
    setState(cur.current);
  }, []);

  const reset = useCallback(() => { queue.current = []; cur.current = INITIAL; setState(INITIAL); }, []);

  useEffect(() => () => { if (slowTimer.current) clearTimeout(slowTimer.current); }, []);

  return { anim: state, begin, onEvent, fail, reset };
}
