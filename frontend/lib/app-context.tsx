"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { MotionConfig } from "motion/react";
import S, { type StringKey } from "@/i18n/strings";
import { clearAll, load, save } from "./storage";
import type { AnimLevel, ChatMessage, Lang, Profile, SchemeCard } from "./types";
import type { GajjuState } from "@/components/Gajju";

type Theme = "system" | "light" | "dark";
export interface Toast { id: number; text: string; tone?: "ok" | "info" | "warn"; icon?: string }

interface Ctx {
  ready: boolean;
  lang: Lang; setLang: (l: Lang) => void;
  t: (k: StringKey, vars?: Record<string, string | number>) => string;
  anim: AnimLevel; setAnim: (a: AnimLevel) => void; motionOK: boolean; reducedMotion: boolean;
  theme: Theme; setTheme: (t: Theme) => void;
  textSize: "normal" | "large"; setTextSize: (s: "normal" | "large") => void;
  onboarded: boolean; setOnboarded: (b: boolean) => void;
  profile: Profile; setProfile: (p: Profile | ((p: Profile) => Profile)) => void;
  messages: ChatMessage[]; setMessages: (m: ChatMessage[] | ((m: ChatMessage[]) => ChatMessage[])) => void;
  chatMeta: { pending: string[]; asked: string[]; focus: string[] };
  setChatMeta: (m: { pending: string[]; asked: string[]; focus: string[] }) => void;
  saved: SchemeCard[]; replaceSaved: (c: SchemeCard[]) => void; isSaved: (id: string) => boolean; toggleSave: (c: SchemeCard, from?: DOMRect | null) => void;
  toasts: Toast[]; toast: (text: string, tone?: Toast["tone"], icon?: string) => void; dismissToast: (id: number) => void;
  mascot: GajjuState; setMascot: (s: GajjuState, holdMs?: number) => void;
  squirrel: { from: DOMRect; key: number } | null; savedBounce: number;
  clearData: () => void;
  online: boolean;
}

const AppCtx = createContext<Ctx | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [lang, setLangState] = useState<Lang>("te");
  const [anim, setAnimState] = useState<AnimLevel>("full");
  const [theme, setThemeState] = useState<Theme>("system");
  const [textSize, setTextSizeState] = useState<"normal" | "large">("normal");
  const [onboarded, setOnboardedState] = useState(false);
  const [profile, setProfileState] = useState<Profile>({});
  const [messages, setMessagesState] = useState<ChatMessage[]>([]);
  const [chatMeta, setChatMetaState] = useState({ pending: [] as string[], asked: [] as string[], focus: [] as string[] });
  const [saved, setSaved] = useState<SchemeCard[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [mascot, setMascotState] = useState<GajjuState>("idle");
  const [squirrel, setSquirrel] = useState<Ctx["squirrel"]>(null);
  const [savedBounce, setSavedBounce] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [online, setOnline] = useState(true);
  const mascotTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // hydrate from device storage
  useEffect(() => {
    const navLang = (navigator.language || "").slice(0, 2);
    setLangState(load<Lang>("lang", navLang === "hi" ? "hi" : navLang === "en" ? "en" : "te"));
    setAnimState(load<AnimLevel>("anim", "full"));
    setThemeState(load<Theme>("theme", "system"));
    setTextSizeState(load("textSize", "normal"));
    setOnboardedState(load("onboarded", false));
    setProfileState(load<Profile>("profile", {}));
    setMessagesState(load<ChatMessage[]>("messages", []).map((m) => ({ ...m, streaming: false })));
    setChatMetaState(load("chatMeta", { pending: [], asked: [], focus: [] }));
    setSaved(load<SchemeCard[]>("saved", []));
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const onMq = () => setReducedMotion(mq.matches);
    mq.addEventListener("change", onMq);
    setOnline(navigator.onLine);
    const on = () => setOnline(true), off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    setReady(true);
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
    return () => { mq.removeEventListener("change", onMq); window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);

  useEffect(() => {
    const el = document.documentElement;
    el.lang = lang;
    el.dataset.anim = anim;
    el.dataset.text = textSize;
    if (theme === "system") delete el.dataset.theme; else el.dataset.theme = theme;
    const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#0f1a1e" : "#0b6e84");
  }, [lang, anim, theme, textSize]);

  const setMascot = useCallback((s: GajjuState, holdMs?: number) => {
    if (mascotTimer.current) clearTimeout(mascotTimer.current);
    setMascotState(s);
    if (holdMs) mascotTimer.current = setTimeout(() => setMascotState("idle"), holdMs);
  }, []);

  const setLang = useCallback((l: Lang) => {
    setLangState((prev) => {
      if (prev !== l) setMascot("language_switch", 1400);
      return l;
    });
    save("lang", l);
  }, [setMascot]);

  const t = useCallback((k: StringKey, vars?: Record<string, string | number>) => {
    let s: string = S[k]?.[lang] ?? S[k]?.en ?? k;
    if (vars) for (const [a, b] of Object.entries(vars)) s = s.replaceAll(`{${a}}`, String(b));
    return s;
  }, [lang]);

  const toast = useCallback((text: string, tone: Toast["tone"] = "ok", icon?: string) => {
    const id = Date.now() + Math.random();
    setToasts((ts) => [...ts.slice(-2), { id, text, tone, icon }]);
    setTimeout(() => setToasts((ts) => ts.filter((x) => x.id !== id)), 3600);
  }, []);
  const dismissToast = useCallback((id: number) => setToasts((ts) => ts.filter((x) => x.id !== id)), []);

  const setProfile = useCallback((p: Profile | ((p: Profile) => Profile)) => {
    setProfileState((prev) => { const next = typeof p === "function" ? p(prev) : p; save("profile", next); return next; });
  }, []);
  const setMessages = useCallback((m: ChatMessage[] | ((m: ChatMessage[]) => ChatMessage[])) => {
    setMessagesState((prev) => {
      const next = typeof m === "function" ? m(prev) : m;
      if (!next.some((x) => x.streaming)) save("messages", next.slice(-40));
      return next;
    });
  }, []);
  const setChatMeta = useCallback((m: Ctx["chatMeta"]) => { setChatMetaState(m); save("chatMeta", m); }, []);

  const isSaved = useCallback((id: string) => saved.some((s) => s.scheme_id === id), [saved]);
  const toggleSave = useCallback((c: SchemeCard, from?: DOMRect | null) => {
    setSaved((prev) => {
      const exists = prev.some((s) => s.scheme_id === c.scheme_id);
      const next = exists ? prev.filter((s) => s.scheme_id !== c.scheme_id) : [c, ...prev];
      save("saved", next);
      if (!exists) {
        if (from) setSquirrel({ from, key: Date.now() });
        setTimeout(() => setSavedBounce((n) => n + 1), from ? 900 : 0);
        toast(S.toastSaved[lang], "ok", "🐿️");
      } else toast(S.toastRemoved[lang], "info");
      return next;
    });
  }, [lang, toast]);

  const clearData = useCallback(() => {
    clearAll();
    setProfileState({}); setMessagesState([]); setSaved([]); setChatMetaState({ pending: [], asked: [], focus: [] });
    save("onboarded", true); save("lang", lang);
  }, [lang]);

  const motionOK = anim !== "off" && !reducedMotion;
  const value = useMemo<Ctx>(() => ({
    ready, lang, setLang, t, anim, setAnim: (a) => { setAnimState(a); save("anim", a); }, motionOK, reducedMotion,
    theme, setTheme: (x) => { setThemeState(x); save("theme", x); },
    textSize, setTextSize: (x) => { setTextSizeState(x); save("textSize", x); },
    onboarded, setOnboarded: (b) => { setOnboardedState(b); save("onboarded", b); },
    profile, setProfile, messages, setMessages, chatMeta, setChatMeta,
    saved, replaceSaved: (c) => { setSaved(c); save("saved", c); }, isSaved, toggleSave, toasts, toast, dismissToast, mascot, setMascot, squirrel, savedBounce, clearData, online,
  }), [ready, lang, setLang, t, anim, motionOK, reducedMotion, theme, textSize, onboarded, profile, setProfile, messages, setMessages,
       chatMeta, setChatMeta, saved, isSaved, toggleSave, toasts, toast, dismissToast, mascot, setMascot, squirrel, savedBounce, clearData, online]);

  return (
    <AppCtx.Provider value={value}>
      <MotionConfig reducedMotion={anim === "off" ? "always" : "user"} transition={anim === "calm" ? { duration: 0.25 } : undefined}>
        {children}
      </MotionConfig>
    </AppCtx.Provider>
  );
}

export function useApp(): Ctx {
  const c = useContext(AppCtx);
  if (!c) throw new Error("useApp outside AppProvider");
  return c;
}
