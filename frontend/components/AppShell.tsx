"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState, type ReactNode } from "react";
import clsx from "clsx";
import { Bookmark, ClipboardCheck, Info, MessageCircle, Settings2, WifiOff } from "lucide-react";
import { useApp } from "@/lib/app-context";
import type { Lang } from "@/lib/types";
import Gajju from "./Gajju";
import { Fireflies, Squirrel } from "./animals";
import { Button, IconButton, Segmented, Toasts } from "./ui";
import { spring } from "@/animations/motion";

const NAV = [
  { href: "/", key: "navChat", icon: MessageCircle },
  { href: "/check", key: "navCheck", icon: ClipboardCheck },
  { href: "/saved", key: "navSaved", icon: Bookmark },
  { href: "/about", key: "navAbout", icon: Info },
] as const;

export function LanguageSwitch({ size = "sm" }: { size?: "sm" | "md" }) {
  const { lang, setLang } = useApp();
  return (
    <Segmented<Lang> size={size} label="Language" value={lang} onChange={setLang}
      options={[
        { value: "en", label: "EN", aria: "English" },
        { value: "hi", label: "हिं", aria: "हिंदी" },
        { value: "te", label: "తె", aria: "తెలుగు" },
      ]} />
  );
}

function TopBar() {
  const { t, mascot, setMascot } = useApp();
  const router = useRouter();
  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-sand/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-2 px-4 lg:px-6">
        <button onClick={() => { setMascot("wave", 1600); router.push("/"); }} className="-ml-1 flex items-center gap-2 rounded-2xl pr-2" aria-label="Haathi home">
          <Gajju state={mascot} size={46} />
          <span className="text-xl font-extrabold tracking-tight text-peacock">{t("appName")}</span>
        </button>
        <div className="flex-1" />
        <LanguageSwitch />
        <Link href="/settings" aria-label={t("settings")}><IconButton label={t("settings")} tabIndex={-1}><Settings2 size={22} /></IconButton></Link>
      </div>
    </header>
  );
}

function NavItems({ vertical }: { vertical?: boolean }) {
  const path = usePathname();
  const { t, savedBounce, saved } = useApp();
  return (
    <>
      {NAV.map(({ href, key, icon: Icon }) => {
        const active = href === "/" ? path === "/" : path.startsWith(href);
        const isSaved = href === "/saved";
        return (
          <Link key={href} href={href} id={isSaved ? (vertical ? "nav-saved-rail" : "nav-saved") : undefined}
            aria-current={active ? "page" : undefined}
            className={clsx("relative flex items-center justify-center gap-1 rounded-2xl font-semibold transition-colors",
              vertical ? "h-14 w-full flex-row justify-start gap-3 px-4" : "h-16 flex-1 flex-col text-[.78rem]",
              active ? "text-peacock" : "text-ink-3 hover:text-ink")}>
            {active && (vertical
              ? <motion.span layoutId="nav-ind-v" className="absolute inset-0 -z-10 rounded-2xl bg-peacock-soft" transition={spring} />
              : <motion.span layoutId="nav-ind" className="absolute top-0 h-[3px] w-10 rounded-b-full bg-peacock" transition={spring} />)}
            <motion.span key={isSaved ? savedBounce : 0} animate={isSaved && savedBounce ? { scale: [1, 1.35, 0.9, 1.1, 1], rotate: [0, -10, 8, 0] } : {}}
              transition={{ duration: 0.6 }} className="relative">
              <Icon size={24} strokeWidth={active ? 2.4 : 2} />
              {isSaved && saved.length > 0 && (
                <span className="absolute -right-2 -top-1.5 grid h-[18px] min-w-[18px] place-items-center rounded-full bg-marigold px-1 text-[10px] font-bold text-[#3a2600]">{saved.length}</span>
              )}
            </motion.span>
            <span className={vertical ? "text-[1rem]" : ""}>{t(key)}</span>
          </Link>
        );
      })}
    </>
  );
}

/** 🐿️ Squirrel grabs the card like an acorn and runs into the Saved tab, which bounces. */
function SquirrelFlight() {
  const { squirrel, motionOK } = useApp();
  const [target, setTarget] = useState<DOMRect | null>(null);
  useEffect(() => {
    if (!squirrel) return;
    const el = [document.getElementById("nav-saved"), document.getElementById("nav-saved-rail")].find((e) => e && e.offsetParent !== null);
    setTarget(el?.getBoundingClientRect() ?? null);
  }, [squirrel]);
  if (!squirrel || !target || !motionOK) return null;
  const from = squirrel.from;
  const sx = from.left + from.width - 40, sy = from.top + 10;
  const tx = target.left + target.width / 2 - 22, ty = target.top + 4;
  return (
    <motion.div key={squirrel.key} className="pointer-events-none fixed left-0 top-0 z-[70]" aria-hidden
      initial={{ x: sx, y: sy, opacity: 0, scale: 0.6 }}
      animate={{ x: [sx, sx - 30, (sx + tx) / 2, tx], y: [sy, sy - 50, Math.min(sy, ty) - 120, ty], opacity: [0, 1, 1, 0], scale: [0.6, 1, 1, 0.5], rotate: [0, -10, 10, 0] }}
      transition={{ duration: 1, times: [0, 0.2, 0.6, 1], ease: "easeInOut" }}>
      <Squirrel size={48} />
    </motion.div>
  );
}

/** Free hosting puts the backend to sleep when idle; tell people it is waking up instead of looking broken. */
function ServerBanner() {
  const { lang } = useApp();
  const [state, setState] = useState<"ok" | "waking" | "down">("ok");
  useEffect(() => {
    let alive = true, tries = 0;
    const ping = async () => {
      try {
        const r = await fetch("/api/health", { cache: "no-store", signal: AbortSignal.timeout(6000) });
        if (!alive) return;
        if (r.ok) { setState("ok"); return; }
        throw new Error();
      } catch {
        if (!alive) return;
        tries++;
        setState(tries > 30 ? "down" : "waking");
        setTimeout(ping, 5000);
      }
    };
    ping();
    return () => { alive = false; };
  }, []);
  const text = {
    waking: { en: "Haathi's server is waking up (free hosting). This can take a minute…", hi: "हाथी का सर्वर जाग रहा है (मुफ़्त होस्टिंग)। एक मिनट लग सकता है…", te: "హాథీ సర్వర్ మేల్కొంటోంది (ఉచిత హోస్టింగ్). ఒక నిమిషం పట్టవచ్చు…" },
    down: { en: "Haathi's server isn't responding right now. Please try again later.", hi: "हाथी का सर्वर अभी जवाब नहीं दे रहा। कृपया बाद में कोशिश करें।", te: "హాథీ సర్వర్ ఇప్పుడు స్పందించడం లేదు. దయచేసి తర్వాత ప్రయత్నించండి." },
  } as const;
  return (
    <AnimatePresence>
      {state !== "ok" && (
        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
          className="overflow-hidden bg-amber-soft text-[#7a4a00] dark:text-marigold" role="status">
          <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2.5 text-sm font-medium">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />
            {text[state][lang]}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function OfflineBanner() {
  const { online, t } = useApp();
  return (
    <AnimatePresence>
      {!online && (
        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
          className="relative overflow-hidden bg-[#0d1b2a] text-[#f6efd9]" role="status">
          <Fireflies count={10} />
          <div className="relative mx-auto flex max-w-6xl items-center gap-2 px-4 py-2.5 text-sm">
            <WifiOff size={16} /> <span>🌙 {t("offline")}</span>
            <Link href="/saved" className="ml-auto font-semibold text-marigold underline-offset-2 hover:underline">{t("navSaved")} →</Link>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

interface BIPEvent extends Event { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> }

/** Install prompt: a small card with the icon; Gajju bounces once to draw attention, not repeatedly. */
function InstallPrompt() {
  const { t } = useApp();
  const [evt, setEvt] = useState<BIPEvent | null>(null);
  const [hidden, setHidden] = useState(true);
  useEffect(() => {
    const h = (e: Event) => {
      e.preventDefault();
      setEvt(e as BIPEvent);
      try { if (!localStorage.getItem("haathi:installDismissed")) setHidden(false); } catch { setHidden(false); }
    };
    window.addEventListener("beforeinstallprompt", h);
    return () => window.removeEventListener("beforeinstallprompt", h);
  }, []);
  const dismiss = () => { setHidden(true); try { localStorage.setItem("haathi:installDismissed", "1"); } catch { /* */ } };
  return (
    <AnimatePresence>
      {evt && !hidden && (
        <motion.div initial={{ y: 80, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 80, opacity: 0 }} transition={spring}
          className="fixed inset-x-3 bottom-[calc(84px+env(safe-area-inset-bottom))] z-40 mx-auto flex max-w-md items-center gap-3 rounded-3xl border border-line bg-surface p-3 shadow-lift lg:bottom-6">
          <motion.img src="/icons/icon.svg" alt="" className="h-14 w-14 rounded-2xl" animate={{ y: [0, -10, 0, -4, 0] }} transition={{ duration: 0.9, delay: 0.4 }} />
          <div className="min-w-0 flex-1">
            <p className="font-bold">{t("install")}</p>
            <p className="text-sm text-ink-2">{t("installBody")}</p>
          </div>
          <div className="flex flex-col gap-1">
            <Button size="sm" onClick={async () => { await evt.prompt(); dismiss(); }}>{t("install")}</Button>
            <button className="text-xs text-ink-3" onClick={dismiss}>{t("notNow")}</button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/** Splash: Gajju blinks and waves his trunk once, then fades into the app. Once per session. */
function Splash() {
  const { motionOK, ready } = useApp();
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!ready || !motionOK) return;
    let seen = false;
    try { seen = sessionStorage.getItem("haathi:splash") === "1"; } catch { /* */ }
    if (seen) return;
    setShow(true);
    // the flag is set when the splash finishes, so a re-run of this effect (Strict Mode) still hides it
    const tm = setTimeout(() => { setShow(false); try { sessionStorage.setItem("haathi:splash", "1"); } catch { /* */ } }, 1500);
    return () => { clearTimeout(tm); setShow(false); };
  }, [ready, motionOK]);
  return (
    <AnimatePresence>
      {show && (
        <motion.div className="fixed inset-0 z-[100] grid place-items-center bg-peacock" exit={{ opacity: 0 }} transition={{ duration: 0.4 }} aria-hidden>
          <motion.div initial={{ scale: 0.7, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: "spring", stiffness: 260, damping: 18 }}
            className="grid place-items-center gap-3 rounded-[44px] bg-white/10 p-6">
            <Gajju state="wave" size={150} decorative />
            <p className="text-2xl font-extrabold tracking-tight text-white">Haathi · హాథీ · हाथी</p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const { ready, onboarded, t } = useApp();
  const path = usePathname();
  const router = useRouter();
  const bare = path.startsWith("/welcome");
  useEffect(() => {
    if (ready && !onboarded && !bare && !path.startsWith("/playground")) router.replace("/welcome");
  }, [ready, onboarded, bare, path, router]);

  if (bare) return <>{children}<Toasts /></>;
  return (
    <div className="paper-texture min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[200] focus:rounded-xl focus:bg-surface focus:p-3">Skip to content</a>
      <Splash />
      <TopBar />
      <OfflineBanner />
      <ServerBanner />
      <div className="mx-auto flex max-w-6xl">
        <nav aria-label="Main" className="sticky top-16 hidden h-[calc(100dvh-4rem)] w-56 shrink-0 flex-col gap-1 p-4 lg:flex">
          <NavItems vertical />
          <div className="mt-auto rounded-2xl bg-surface p-3 text-xs leading-relaxed text-ink-3">{t("disclaimer")}</div>
        </nav>
        <main id="main" className="min-w-0 flex-1 pb-[calc(76px+env(safe-area-inset-bottom))] lg:pb-0">{children}</main>
      </div>
      <nav aria-label="Main" className="safe-bottom fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 backdrop-blur-md lg:hidden">
        <div className="mx-auto flex max-w-xl px-2"><NavItems /></div>
      </nav>
      <SquirrelFlight />
      <InstallPrompt />
      <Toasts />
    </div>
  );
}
