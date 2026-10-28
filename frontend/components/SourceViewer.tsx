"use client";

import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { motion } from "motion/react";
import { ExternalLink, Maximize2, ZoomIn } from "lucide-react";
import { useApp } from "@/lib/app-context";
import { getJSON } from "@/lib/api";
import type { Citation, PageLayout } from "@/lib/types";
import { Sheet, useMediaQuery } from "./ui";

interface SourceCtx {
  current: Citation | null; layoutId: string | null;
  open: (c: Citation, layoutId?: string) => void; close: () => void;
  setDocked: (b: boolean) => void; docked: boolean;
}
const Ctx = createContext<SourceCtx | null>(null);

export function SourceProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<Citation | null>(null);
  const [layoutId, setLayoutId] = useState<string | null>(null);
  const [docked, setDocked] = useState(false);
  const wide = useMediaQuery("(min-width: 1024px)");
  const { t } = useApp();
  const open = useCallback((c: Citation, id?: string) => { setCurrent(c); setLayoutId(id ?? null); }, []);
  const close = useCallback(() => { setCurrent(null); setLayoutId(null); }, []);
  const value = useMemo(() => ({ current, layoutId, open, close, setDocked, docked }), [current, layoutId, open, close, docked]);
  return (
    <Ctx.Provider value={value}>
      {children}
      {!(docked && wide) && (
        <Sheet open={!!current} onClose={close} title={current?.title ?? t("sources")} side={wide}>
          {current && <SourcePage citation={current} />}
        </Sheet>
      )}
    </Ctx.Provider>
  );
}

export function useSource(): SourceCtx {
  const c = useContext(Ctx);
  if (!c) return { current: null, layoutId: null, open: () => {}, close: () => {}, setDocked: () => {}, docked: false };
  return c;
}

/** Fetches a page layout and renders it with the cited passage highlighted. */
export function SourcePage({ citation }: { citation: Citation }) {
  const { t } = useApp();
  const [page, setPage] = useState<PageLayout | null>(null);
  const [err, setErr] = useState(false);
  const [n, setN] = useState(citation.page);
  useEffect(() => { setN(citation.page); }, [citation]);
  useEffect(() => {
    let live = true;
    setPage(null); setErr(false);
    const q = n === citation.page && citation.quote ? `?quote=${encodeURIComponent(citation.quote)}` : "";
    getJSON<PageLayout>(`/api/sources/${encodeURIComponent(citation.doc)}/page/${n}${q}`)
      .then((p) => live && setPage(p)).catch(() => live && setErr(true));
    return () => { live = false; };
  }, [citation, n]);

  return (
    <div className="pb-4">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        {page?.pages.map((p) => (
          <button key={p} onClick={() => setN(p)} aria-pressed={p === n}
            className={`h-10 rounded-full px-3.5 font-semibold ${p === n ? "bg-peacock text-white dark:text-[#06242b]" : "bg-ink/[.06] text-ink-2"}`}>
            {t("page", { n: p })}
          </button>
        ))}
        {page?.source_url && (
          <a href={page.source_url} target="_blank" rel="noreferrer" className="ml-auto inline-flex h-10 items-center gap-1.5 rounded-full px-3 font-semibold text-peacock hover:bg-peacock-soft">
            {t("openSource")} <ExternalLink size={15} />
          </a>
        )}
      </div>
      {citation.quote && (
        <blockquote className="mb-3 rounded-2xl border-l-4 border-marigold bg-amber-soft/60 px-3.5 py-2.5 text-[.95rem] italic leading-snug">“{citation.quote}”</blockquote>
      )}
      {err && <p className="text-coral">{t("errorBody")}</p>}
      {!page && !err && <div className="shimmer aspect-[595/842] w-full rounded-2xl" />}
      {page && (page.kind === "pdf" && page.file_url ? <PdfPage layout={page} /> : page.kind === "html" ? <HtmlPage layout={page} /> : <LayoutPage layout={page} />)}
      {page?.kind === "seed" && <p className="mt-2 text-xs text-ink-3">ⓘ {t("seedNotice")}</p>}
      {page?.last_verified && <p className="mt-1 text-xs text-ink-3">{t("lastVerified", { d: page.last_verified })}</p>}
    </div>
  );
}

/** Seed documents: every line has an exact bbox, so we draw the page as SVG and highlight precisely. */
function LayoutPage({ layout }: { layout: PageLayout }) {
  const { motionOK } = useApp();
  const textRefs = useRef<Map<string, SVGTextElement>>(new Map());
  const [rects, setRects] = useState<{ x: number; y: number; w: number; h: number }[]>([]);
  const [zoomed, setZoomed] = useState(false);

  useLayoutEffect(() => {
    const out: typeof rects = [];
    for (const h of layout.highlights) {
      const el = textRefs.current.get(`${h.block}:${h.line}`);
      if (!el) continue;
      try {
        const x0 = h.start > 0 ? el.getSubStringLength(0, h.start) : 0;
        const w = el.getSubStringLength(h.start, Math.max(1, h.end - h.start));
        out.push({ x: h.bbox[0] + x0 - 2, y: h.bbox[1] + 1, w: w + 4, h: h.bbox[3] - h.bbox[1] - 1 });
      } catch {
        out.push({ x: h.bbox[0], y: h.bbox[1], w: h.bbox[2] - h.bbox[0], h: h.bbox[3] - h.bbox[1] });
      }
    }
    setRects(out);
    setZoomed(false);
    const tm = setTimeout(() => setZoomed(out.length > 0), motionOK ? 450 : 0);
    return () => clearTimeout(tm);
  }, [layout, motionOK]);

  const hb = layout.highlight_bbox;
  const W = layout.width, H = layout.height;
  // zoom so the passage fills ~85% of the width, centred vertically
  const zoom = hb ? Math.min(2.2, Math.max(1.35, (W * 0.92) / Math.max(hb[2] - hb[0] + 30, 160))) : 1;
  const cx = hb ? (hb[0] + hb[2]) / 2 : W / 2, cy = hb ? (hb[1] + hb[3]) / 2 : H / 2;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-line bg-[#fffef9] shadow-card dark:bg-[#f4efe4]">
      <motion.svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label={`${layout.title}, page ${layout.page}`}
        style={{ transformOrigin: `${(cx / W) * 100}% ${(cy / H) * 100}%` }}
        animate={{ scale: zoomed ? zoom : 1 }} transition={{ type: "spring", stiffness: 120, damping: 22 }}>
        <rect width={W} height={H} fill="transparent" />
        {rects.map((r, i) => (
          <motion.rect key={i} x={r.x} y={r.y} width={r.w} height={r.h} rx={3} fill="#f4a51c" fillOpacity={0.42}
            style={{ transformOrigin: `${r.x}px ${r.y}px`, transformBox: "view-box" }}
            initial={{ scaleX: motionOK ? 0 : 1 }} animate={{ scaleX: 1 }}
            transition={{ duration: 0.45, delay: (motionOK ? 0.75 : 0) + i * 0.18, ease: "easeOut" }} />
        ))}
        {layout.blocks.map((b) =>
          b.lines.map((ln, li) => (
            <text key={`${b.id}-${li}`} ref={(el) => { if (el) textRefs.current.set(`${b.id}:${li}`, el); }}
              x={ln.bbox[0]} y={ln.bbox[3] - (ln.bbox[3] - ln.bbox[1]) * 0.3} fontSize={b.font_size}
              fontWeight={b.type === "title" ? 800 : b.type === "heading" ? 700 : 400}
              fill={b.type === "note" ? "#6f7d82" : b.type === "heading" || b.type === "title" ? "#07505f" : "#1b2a30"}
              fontStyle={b.type === "note" ? "italic" : undefined}
              style={{ fontFamily: "var(--font-noto), sans-serif" }}>{ln.text}</text>
          )),
        )}
      </motion.svg>
      {hb && (
        <button onClick={() => setZoomed((z) => !z)} aria-label={zoomed ? "Fit page" : "Zoom to passage"}
          className="absolute bottom-2 right-2 grid h-11 w-11 place-items-center rounded-full bg-ink/80 text-white shadow-card">
          {zoomed ? <Maximize2 size={18} /> : <ZoomIn size={18} />}
        </button>
      )}
    </div>
  );
}

/** Official web pages (e.g. RBI circulars): show the text with the cited block highlighted. */
function HtmlPage({ layout }: { layout: PageLayout }) {
  const hit = new Set(layout.highlights.map((h) => h.block));
  return (
    <div className="max-h-[70vh] space-y-2 overflow-y-auto rounded-2xl border border-line bg-[#fffef9] p-4 text-[.92rem] leading-relaxed text-[#1b2a30]">
      {layout.blocks.map((b) => (
        <p key={b.id} className={hit.has(b.id) ? "rounded bg-[#f4a51c]/40 px-1" : ""}>{b.lines.map((l) => l.text).join(" ")}</p>
      ))}
    </div>
  );
}

/** Official PDFs (after `make ingest` with Docling): render with pdf.js and overlay the cited bbox. */
function PdfPage({ layout }: { layout: PageLayout }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const pdfjs = await import("pdfjs-dist");
      pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
      const doc = await pdfjs.getDocument(layout.file_url!).promise;
      const p = await doc.getPage(layout.page);
      const vp = p.getViewport({ scale: 2 });
      const c = canvas.current;
      if (!c || cancelled) return;
      c.width = vp.width; c.height = vp.height;
      await p.render({ canvasContext: c.getContext("2d")!, viewport: vp, canvas: c } as never).promise;
      setSize({ w: vp.width / 2, h: vp.height / 2 });
    })().catch(() => {});
    return () => { cancelled = true; };
  }, [layout]);
  const hb = layout.highlight_bbox;
  return (
    <div className="relative overflow-hidden rounded-2xl border border-line bg-white">
      <canvas ref={canvas} className="block h-auto w-full" />
      {size && hb && (
        <motion.div className="absolute rounded bg-[#f4a51c]/40" style={{ left: `${(hb[0] / size.w) * 100}%`, top: `${(hb[1] / size.h) * 100}%`,
          width: `${((hb[2] - hb[0]) / size.w) * 100}%`, height: `${((hb[3] - hb[1]) / size.h) * 100}%`, transformOrigin: "left" }}
          initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.6, delay: 0.3 }} />
      )}
    </div>
  );
}
