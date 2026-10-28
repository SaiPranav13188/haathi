"""Parse source documents into pages → blocks → lines with bounding boxes.

* Official PDFs/HTML are parsed with Docling when it is installed (`uv sync --extra ml`); its layout gives
  headings, tables and page bounding boxes.
* Seed summaries (data/seed/docs/*.md) go through a small deterministic layout engine: A4 pages, fixed
  fonts and wrap widths, so every line has an exact bbox and the source viewer can highlight a quote
  precisely.

Coordinates are PDF points with the origin at the top-left of the page: bbox = [x0, y0, x1, y1].
"""
from __future__ import annotations

import json
import re
import textwrap
from dataclasses import asdict, dataclass, field
from pathlib import Path

PAGE_W, PAGE_H, MARGIN = 595.0, 842.0, 56.0
STYLE = {  # font size, line height, wrap width (chars), indent
    "title": (17.0, 23.0, 52, 0.0),
    "note": (8.5, 12.5, 104, 0.0),
    "heading": (12.5, 18.0, 72, 0.0),
    "para": (10.0, 15.0, 88, 0.0),
    "list": (10.0, 15.0, 84, 14.0),
    "table": (9.0, 14.0, 96, 0.0),
}
CHAR_W = 0.5  # average glyph width as a fraction of font size (Noto Sans)


@dataclass
class Line:
    text: str
    bbox: list[float]


@dataclass
class Block:
    id: str
    type: str
    text: str
    bbox: list[float]
    font_size: float
    lines: list[Line] = field(default_factory=list)
    section: str | None = None
    rows: list[list[str]] | None = None  # table rows (first row = header)


@dataclass
class Page:
    page: int
    width: float
    height: float
    blocks: list[Block] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(b.text for b in self.blocks)


@dataclass
class ParsedDoc:
    doc_id: str
    title: str
    source_url: str | None
    kind: str  # "seed" | "pdf" | "html"
    pages: list[Page]

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, d: dict) -> "ParsedDoc":
        pages = []
        for p in d["pages"]:
            blocks = [Block(**{**b, "lines": [Line(**ln) for ln in b["lines"]]}) for b in p["blocks"]]
            pages.append(Page(p["page"], p["width"], p["height"], blocks))
        return cls(d["doc_id"], d["title"], d.get("source_url"), d["kind"], pages)

    def page(self, n: int) -> Page:
        return next(p for p in self.pages if p.page == n)


_URL = re.compile(r"https?://\S+")


def parse_seed_markdown(path: Path) -> ParsedDoc:
    raw = path.read_text(encoding="utf-8")
    doc_id = path.name
    pages: list[Page] = []
    title = ""
    source_url = None
    current: Page | None = None
    y = MARGIN
    section: str | None = None
    counter = 0

    def new_page(n: int) -> Page:
        nonlocal y
        y = MARGIN
        p = Page(n, PAGE_W, PAGE_H)
        pages.append(p)
        return p

    def emit(kind: str, text: str, rows: list[list[str]] | None = None) -> None:
        nonlocal y, counter, current
        if current is None:
            current = new_page(1)
        size, lh, width, indent = STYLE[kind]
        x0 = MARGIN + indent
        wrapped = textwrap.wrap(text, width=width) if kind != "table" else [" | ".join(r) for r in rows or []]
        if kind == "heading" and current.blocks:
            y += 8
        top = y
        lines = []
        for ln in wrapped:
            w = min(len(ln) * size * CHAR_W, PAGE_W - MARGIN - x0)
            lines.append(Line(ln, [round(x0, 1), round(y, 1), round(x0 + w, 1), round(y + lh, 1)]))
            y += lh
        y += 6 if kind in {"para", "note", "table"} else 3
        right = max((ln.bbox[2] for ln in lines), default=x0)
        counter += 1
        current.blocks.append(Block(f"b{counter}", kind, text, [round(x0, 1), round(top, 1), round(right, 1), round(y, 1)],
                                    size, lines, section, rows))

    table: list[list[str]] = []
    for line in raw.splitlines() + [""]:
        s = line.strip()
        if table and not s.startswith("|"):
            emit("table", " ; ".join(", ".join(r) for r in table[1:]), rows=table)
            table = []
        m = re.match(r"<!--\s*page\s+(\d+)\s*-->", s)
        if m:
            n = int(m.group(1))
            if current is None or current.page != n:
                current = new_page(n)
            continue
        if not s:
            continue
        if s.startswith("# "):
            title = s[2:].strip()
            emit("title", title)
        elif s.startswith("> "):
            note = s[2:].strip()
            if (u := _URL.search(note)) and source_url is None:
                source_url = u.group(0).rstrip(".;,")
            emit("note", note)
        elif s.startswith("## "):
            section = re.sub(r"^\d+\.\s*", "", s[3:].strip())
            emit("heading", s[3:].strip())
        elif s.startswith("- "):
            emit("list", "• " + s[2:].strip())
        elif s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                table.append(cells)
        else:
            emit("para", s)
    # the pre-page-1 title/note blocks land on page 1
    return ParsedDoc(doc_id, title, source_url, "seed", pages)


def parse_with_docling(path: Path, source_url: str | None = None) -> ParsedDoc:  # pragma: no cover - needs ml extra
    """Parse an official PDF/HTML with Docling, keeping headings, tables (as rows) and bounding boxes."""
    from docling.document_converter import DocumentConverter

    result = DocumentConverter().convert(str(path))
    dl = result.document
    pages: dict[int, Page] = {}
    for no, p in dl.pages.items():
        pages[no] = Page(no, float(p.size.width), float(p.size.height))
    counter = 0
    section = None
    for item, _level in dl.iterate_items():
        prov = getattr(item, "prov", None)
        if not prov:
            continue
        pr = prov[0]
        page = pages[pr.page_no]
        b = pr.bbox.to_top_left_origin(page_height=page.height)
        bbox = [round(b.l, 1), round(b.t, 1), round(b.r, 1), round(b.b, 1)]
        label = str(getattr(item, "label", "text"))
        counter += 1
        if "table" in label:
            df = item.export_to_dataframe()
            rows = [list(map(str, df.columns))] + [list(map(str, r)) for r in df.values.tolist()]
            text = " ; ".join(", ".join(f"{h}: {c}" for h, c in zip(rows[0], r)) for r in rows[1:])
            page.blocks.append(Block(f"b{counter}", "table", text, bbox, 9.0, [Line(text[:200], bbox)], section, rows))
            continue
        text = getattr(item, "text", "").strip()
        if not text:
            continue
        kind = "heading" if "header" in label or "title" in label else "list" if "list" in label else "para"
        if kind == "heading":
            section = text
        page.blocks.append(Block(f"b{counter}", kind, text, bbox, 10.0, [Line(text, bbox)], section))
    if not pages:  # HTML has no page geometry: lay the text out as one page with synthetic line boxes
        page = Page(1, PAGE_W, PAGE_H)
        y = MARGIN
        for item, _level in dl.iterate_items():
            text = " ".join(getattr(item, "text", "").split())
            if not text:
                continue
            label = str(getattr(item, "label", "text"))
            kind = "heading" if "header" in label or "title" in label else "list" if "list" in label else "para"
            if kind == "heading":
                section = text
            counter += 1
            h = 15.0 * max(1, len(text) // 88 + 1)
            bbox = [MARGIN, round(y, 1), PAGE_W - MARGIN, round(y + h, 1)]
            page.blocks.append(Block(f"b{counter}", kind, text, bbox, 10.0, [Line(text, bbox)], section))
            y += h + 6
        pages[1] = page
    ordered = [pages[k] for k in sorted(pages)]
    title = next((b.text for p in ordered for b in p.blocks if b.type == "heading"), path.stem)
    return ParsedDoc(path.name, title, source_url, "pdf" if path.suffix.lower() == ".pdf" else "html", ordered)


def parse_html(path: Path, source_url: str | None = None) -> ParsedDoc:
    """Government pages are often table-laid-out; keep every paragraph, cell and list item as a block."""
    import html as _html

    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"(?is)<(script|style|noscript|nav|header|footer)[^>]*>.*?</\1>", " ", raw)
    title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
    parts = re.split(r"(?i)<(?:/?(?:p|div|td|th|li|tr|table|h[1-6])\b[^>]*|br\s*/?)>", raw)
    page = Page(1, PAGE_W, PAGE_H)
    pages = [page]
    y, counter = MARGIN, 0
    seen: set[str] = set()
    for part in parts:
        text = " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", part)).split())
        if len(text) < 25 or text in seen:
            continue
        seen.add(text)
        counter += 1
        lines = textwrap.wrap(text, width=STYLE["para"][2])
        if y + 15 * len(lines) > PAGE_H - MARGIN and page.blocks:  # page full: continue on a new page
            page = Page(len(pages) + 1, PAGE_W, PAGE_H)
            pages.append(page)
            y = MARGIN
        block_lines = []
        top = y
        for ln in lines:
            block_lines.append(Line(ln, [MARGIN, round(y, 1), round(MARGIN + len(ln) * 10 * CHAR_W, 1), round(y + 15, 1)]))
            y += 15
        page.blocks.append(Block(f"b{counter}", "para", text, [MARGIN, round(top, 1), PAGE_W - MARGIN, round(y, 1)], 10.0, block_lines))
        y += 6
    title = " ".join(_html.unescape(title_m.group(1)).split()) if title_m else path.stem
    return ParsedDoc(path.name, title, source_url, "html", pages)


def parse_any(path: Path, source_url: str | None = None) -> ParsedDoc:
    if path.suffix == ".md":
        return parse_seed_markdown(path)
    if path.suffix.lower() in {".html", ".htm"}:
        return parse_html(path, source_url)
    return parse_with_docling(path, source_url)


# ------------------------------------------------------------------ quote location

def _norm(s: str) -> str:
    return " ".join(s.split())


def locate_quote(page: Page, quote: str) -> list[dict]:
    """Return highlight spans [{block, line, start, end, bbox}] for an exact (whitespace-normalised) quote.
    Falls back to fuzzy block matching (rapidfuzz) so Docling text with odd spacing still highlights."""
    q = _norm(quote)
    for b in page.blocks:
        bt = _norm(b.text)
        i = bt.find(q)
        if i < 0:
            continue
        spans, offset = [], 0
        # map char range onto wrapped lines (textwrap collapses single spaces at breaks)
        for li, ln in enumerate(b.lines):
            ls = bt.find(ln.text, offset)
            if ls < 0:
                continue
            le = ls + len(ln.text)
            offset = le
            s, e = max(i, ls), min(i + len(q), le)
            if s < e:
                x0 = ln.bbox[0] + (s - ls) * b.font_size * CHAR_W
                x1 = ln.bbox[0] + (e - ls) * b.font_size * CHAR_W
                spans.append({"block": b.id, "line": li, "start": s - ls, "end": e - ls,
                              "bbox": [round(x0, 1), ln.bbox[1], round(min(x1, ln.bbox[2] + 4), 1), ln.bbox[3]]})
        if spans:
            return spans
    try:
        from rapidfuzz import fuzz
    except ImportError:  # pragma: no cover
        return []
    best = max(page.blocks, key=lambda b: fuzz.partial_ratio(q, _norm(b.text)), default=None)
    if best is not None and fuzz.partial_ratio(q, _norm(best.text)) >= 90:
        return [{"block": best.id, "line": li, "start": 0, "end": len(ln.text), "bbox": ln.bbox} for li, ln in enumerate(best.lines)]
    return []


def union_bbox(spans: list[dict]) -> list[float] | None:
    if not spans:
        return None
    bs = [s["bbox"] for s in spans]
    return [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]


def save(doc: ParsedDoc, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{doc.doc_id}.json"
    p.write_text(json.dumps(doc.to_json(), ensure_ascii=False), encoding="utf-8")
    return p
