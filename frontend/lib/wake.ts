"use client";

/**
 * Free hosting puts the backend to sleep after ~15 idle minutes and it needs ~30-60 s to wake. Every API call
 * goes through ensureAwake(): it checks /api/status (a Vercel-side check that always answers), and while the backend
 * is waking it fires "haathi:waking" so the UI can show a banner, then resolves once the backend answers.
 */
let lastAwake = 0;
let pending: Promise<boolean> | null = null;
const FRESH_MS = 60_000;

function emit(waking: boolean) {
  window.dispatchEvent(new CustomEvent("haathi:waking", { detail: waking }));
}

async function status(): Promise<boolean> {
  try {
    const r = await fetch("/api/status", { cache: "no-store", signal: AbortSignal.timeout(12000) });
    return r.ok && ((await r.json()) as { ok: boolean }).ok;
  } catch {
    return false;
  }
}

export function markAwake() { lastAwake = Date.now(); }

export function ensureAwake(maxWaitMs = 120_000): Promise<boolean> {
  if (Date.now() - lastAwake < FRESH_MS) return Promise.resolve(true);
  pending ??= (async () => {
    const t0 = Date.now();
    let first = true;
    while (Date.now() - t0 < maxWaitMs) {
      if (await status()) { lastAwake = Date.now(); if (!first) emit(false); return true; }
      if (first) { emit(true); first = false; }
      await new Promise((r) => setTimeout(r, 3000));
    }
    emit(false);
    return false;
  })().finally(() => { pending = null; });
  return pending;
}

const RETRYABLE = new Set([502, 503, 504]);

/** fetch with "wait for the backend to wake up" + a few retries on gateway errors. */
export async function wakeFetch(input: string, init?: RequestInit, tries = 3): Promise<Response> {
  for (let i = 0; ; i++) {
    await ensureAwake();
    try {
      const r = await fetch(input, init);
      if (!RETRYABLE.has(r.status) || i >= tries - 1) { if (r.ok) markAwake(); return r; }
    } catch (e) {
      if (i >= tries - 1 || init?.signal?.aborted) throw e;
    }
    lastAwake = 0; // force a fresh status check before retrying
    await new Promise((r) => setTimeout(r, 2000));
  }
}
