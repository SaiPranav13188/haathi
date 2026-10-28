"""Chunking: structure-aware (sections; table rows with headers repeated) and fixed-size (for ablations)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .parse import ParsedDoc


@dataclass
class Chunk:
    id: str
    doc_id: str
    scheme_id: str | None
    page: int
    section: str | None
    text: str
    kind: str  # section | table_row | fixed | card
    block_ids: list[str] = field(default_factory=list)
    context: str = ""
    lang: str = "en"

    @property
    def index_text(self) -> str:
        head = f"{self.section}: " if self.section and self.kind != "card" else ""
        return f"{self.context}\n{head}{self.text}".strip() if self.context else f"{head}{self.text}"

    def to_json(self) -> dict:
        return asdict(self)


def structure_chunks(doc: ParsedDoc, scheme_id: str | None) -> list[Chunk]:
    out: list[Chunk] = []
    for page in doc.pages:
        cur: list = []
        cur_section = None

        def flush() -> None:
            body = [b for b in cur if b.type not in {"title", "note", "heading"}]
            if not body:
                return
            text = " ".join(b.text for b in body)
            out.append(Chunk(f"{doc.doc_id}#p{page.page}-{body[0].id}", doc.doc_id, scheme_id, page.page, cur_section,
                             text, "section", [b.id for b in body]))

        for b in page.blocks:
            if b.type == "table" and b.rows and len(b.rows) > 1:
                flush()
                cur = []
                header = b.rows[0]
                for i, row in enumerate(b.rows[1:], 1):
                    text = "; ".join(f"{h}: {c}" for h, c in zip(header, row))
                    out.append(Chunk(f"{doc.doc_id}#p{page.page}-{b.id}-r{i}", doc.doc_id, scheme_id, page.page,
                                     b.section, text, "table_row", [b.id]))
                continue
            if b.type == "heading":
                flush()
                cur = [b]
                cur_section = b.section
                continue
            cur.append(b)
        flush()
    return out


def fixed_chunks(doc: ParsedDoc, scheme_id: str | None, size: int = 60, stride: int = 45) -> list[Chunk]:
    out: list[Chunk] = []
    for page in doc.pages:
        words = page.text.split()
        for i, start in enumerate(range(0, max(len(words) - size + stride, 1), stride)):
            piece = words[start:start + size]
            if not piece:
                break
            out.append(Chunk(f"{doc.doc_id}#p{page.page}-f{i}", doc.doc_id, scheme_id, page.page, None,
                             " ".join(piece), "fixed", [b.id for b in page.blocks]))
    return out


def card_chunk(scheme: dict) -> Chunk:
    """A multilingual 'name card' per scheme (names + taglines in en/hi/te) so Hindi/Telugu queries can
    find schemes even with the light embedder. Cites page 1 of the scheme's document."""
    parts = []
    for key in ("name", "tagline"):
        parts.extend(v for v in scheme[key].values() if v)
    return Chunk(f"{scheme['doc']}#card", scheme["doc"], scheme["scheme_id"], 1, "About the scheme",
                 " · ".join(parts), "card", [], lang="mixed")
