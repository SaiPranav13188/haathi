"""Loads the scheme rule DB, parsed documents and chunks. Builds missing artefacts from the seed corpus."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from ingestion.chunk import Chunk, card_chunk, fixed_chunks, structure_chunks
from ingestion.parse import ParsedDoc, locate_quote, parse_any, save, union_bbox

from .config import get_settings
from .eligibility.dsl import Scheme

log = logging.getLogger(__name__)

# Extra spellings people actually type (romanised, old names). Old names point at the current scheme and
# trigger a freshness notice.
ALIASES: dict[str, list[str]] = {
    "ts_rythu_bharosa": ["rythu bharosa", "raitu bharosa", "rythu bandhu", "raithu bandhu", "రైతు బంధు", "रायतु बंधु", "rythubandhu"],
    "ts_indiramma_atmiya_bharosa": ["atmiya bharosa", "athmiya bharosa", "landless labour 12000"],
    "ts_rythu_bima": ["rythu bima", "raitu bima", "rythubima", "రైతు బీమా"],
    "ts_kalyana_lakshmi": ["kalyana lakshmi", "kalyan laxmi", "kalyanalakshmi"],
    "ts_shaadi_mubarak": ["shadi mubarak", "shaadi mubarak"],
    "ts_aasara_pension": ["aasara", "asara pension", "cheyutha", "చేయూత"],
    "ts_gruha_jyothi": ["gruha jyothi", "griha jyoti", "free current", "free electricity", "ఉచిత కరెంటు"],
    "ts_mahalakshmi_bus": ["mahalakshmi", "మహాలక్ష్మి", "mahalakshmi bus", "free bus", "ఉచిత బస్సు", "मुफ्त बस"],
    "ts_mahalakshmi_lpg": ["mahalakshmi", "మహాలక్ష్మి", "500 gas", "500 cylinder", "mahalakshmi gas"],
    "ts_indiramma_indlu": ["indiramma illu", "indiramma indlu", "indiramma house", "ఇందిరమ్మ ఇల్లు"],
    "ts_aarogyasri": ["aarogyasri", "arogyasri", "aarogya sri", "आरोग्यश्री", "ఆరోగ్యశ్రీ"],
    "ts_epass_post_matric": ["epass", "e-pass", "fee reimbursement", "ఫీజు రీయింబర్స్‌మెంట్"],
    "pm_kisan": ["pm kisan", "pmkisan", "పీఎం కిసాన్", "पीएम किसान", "पीएम-किसान", "kisan samman", "किसान सम्मान निधि"],
    "pmfby": ["fasal bima", "crop insurance", "పంట బీమా", "फसल बीमा"],
    "kcc": ["kisan credit", "kcc", "crop loan", "పంట రుణం"],
    "pmay_g": ["awas gramin", "pmay g", "pmay-g", "awaas", "आवास योजना ग्रामीण", "ఆవాస్ యోజన గ్రామీణ"],
    "pmay_u": ["pmay u", "pmay-u", "awas urban", "pmay urban", "pmay 2.0", "आवास योजना शहरी", "ఆవాస్ యోజన పట్టణ"],
    "pmjay": ["ayushman", "pmjay", "pm-jay", "आयुष्मान", "ఆయుష్మాన్"],
    "pm_ujjwala": ["ujjwala", "free gas connection", "उज्ज्वला"],
    "sukanya_samriddhi": ["sukanya", "ssy"],
    "apy": ["atal pension", "apy"],
    "pmjjby": ["jeevan jyoti", "pmjjby"],
    "pmsby": ["suraksha bima", "pmsby"],
    "pm_sym": ["shram yogi", "maandhan", "maan dhan", "pm-sym", "pmsym"],
    "ignoaps": ["old age pension", "ignoaps", "vridha pension", "वृद्धावस्था पेंशन"],
    "post_matric_sc": ["post matric", "nsp scholarship", "national scholarship"],
    "pm_vishwakarma": ["vishwakarma", "विश्वकर्मा"],
    "ap_annadata_sukhibhava": ["annadata", "annadatha", "sukhibhava"],
    "ap_thalliki_vandanam": ["thalliki vandanam", "talliki vandanam", "amma vodi", "అమ్మ ఒడి"],
    "ap_ntr_bharosa_pension": ["ntr bharosa", "ysr pension", "pension kanuka"],
}
# alias -> (scheme, old name note)
RENAMED = {"rythu bandhu": "ts_rythu_bharosa", "raithu bandhu": "ts_rythu_bharosa", "రైతు బంధు": "ts_rythu_bharosa",
           "rythubandhu": "ts_rythu_bharosa", "amma vodi": "ap_thalliki_vandanam", "అమ్మ ఒడి": "ap_thalliki_vandanam",
           "ysr pension": "ap_ntr_bharosa_pension", "cheyutha": "ts_aasara_pension", "చేయూత": "ts_aasara_pension"}


class Corpus:
    def __init__(self, chunking: str | None = None, contextual: bool | None = None):
        s = get_settings()
        self.settings = s
        self.chunking = chunking or s.chunking
        self.contextual = s.contextual if contextual is None else contextual
        self.schemes: dict[str, Scheme] = {}
        self.docs: dict[str, ParsedDoc] = {}
        self.chunks: list[Chunk] = []
        self._load()

    # ---------------------------------------------------------------- loading
    def _load(self) -> None:
        s = self.settings
        parsed_dir = s.index_dir / "parsed"
        raw_schemes = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((s.data_dir / "schemes").glob("*.json"))]
        raw_schemes = [r for r in raw_schemes if r.get("review_status") != "rejected"]
        for r in raw_schemes:
            for doc_id in {r["doc"], *(src["doc"] for src in self._sources(r)), *(o["doc"] for o in r.get("official_sources", []))}:
                if doc_id not in self.docs:
                    self.docs[doc_id] = self._load_doc(doc_id, parsed_dir)
        self._doc_owner: dict[str, str] = {}
        for r in raw_schemes:
            for doc_id in [r["doc"], *(src["doc"] for src in self._sources(r)), *(o["doc"] for o in r.get("official_sources", []))]:
                self._doc_owner.setdefault(doc_id, r["scheme_id"])
        for r in raw_schemes:
            self._attach_bboxes(r)
            sc = Scheme.model_validate(r)
            self.schemes[sc.scheme_id] = sc
        # official documents get a readable title ("G.O.Ms.No.47 (TRB), 08/12/2023 · Mahalakshmi Free Bus Travel")
        for sc in self.schemes.values():
            for o in sc.official_sources:
                d = self.docs.get(o.get("doc", ""))
                if d is not None and d.kind != "seed" and o.get("label"):
                    d.title = f"{o['label']} · {sc.name.en}" if o["label"].startswith("G.O") else o["label"]
        self.chunks = self._load_chunks(raw_schemes)

    def _load_doc(self, doc_id: str, parsed_dir: Path) -> ParsedDoc:
        cached = parsed_dir / f"{doc_id}.json"
        if cached.exists():
            return ParsedDoc.from_json(json.loads(cached.read_text(encoding="utf-8")))
        for base in (self.settings.data_dir / "seed" / "docs", self.settings.data_dir / "raw"):
            if (base / doc_id).exists():
                doc = parse_any(base / doc_id)
                save(doc, parsed_dir)
                return doc
        raise FileNotFoundError(f"document {doc_id} not found; run `make ingest`")

    @staticmethod
    def _sources(raw: dict) -> list[dict]:
        return [r["source"] for r in raw["rules"]] + [raw["benefit"]["source"], raw["how_to_apply"]["source"]]

    def _attach_bboxes(self, raw: dict) -> None:
        for src in self._sources(raw):
            doc = self.docs[src["doc"]]
            if src.get("bbox") or not src.get("quote"):
                continue
            try:
                spans = locate_quote(doc.page(src["page"]), src["quote"])
            except StopIteration:
                spans = []
            src["bbox"] = union_bbox(spans)
            if not spans:
                log.warning("quote not found in %s p%s: %s", src["doc"], src["page"], src["quote"][:60])

    def _load_chunks(self, raw_schemes: list[dict]) -> list[Chunk]:
        from ingestion.contextualize import contextualize

        chunks: list[Chunk] = []
        for doc_id, doc in self.docs.items():
            sid = self._doc_owner.get(doc_id)
            chunks.extend(structure_chunks(doc, sid) if self.chunking == "structure" else fixed_chunks(doc, sid))
        if self.contextual:
            contextualize(chunks, self.docs, {r["scheme_id"]: r for r in raw_schemes})
        chunks.extend(card_chunk(r) for r in raw_schemes)
        return chunks

    # ---------------------------------------------------------------- helpers
    def scheme_for_doc(self, doc_id: str) -> Scheme | None:
        sid = self._doc_owner.get(doc_id)
        return self.schemes.get(sid) if sid else None

    def find_mentions(self, text: str) -> list[tuple[str, str | None]]:
        """Return [(scheme_id, old_name_if_renamed)] for schemes named in the text."""
        t = " " + text.lower() + " "
        hits: list[tuple[str, str | None]] = []
        for sid, sc in self.schemes.items():
            names = [n.lower() for n in (sc.name.en, sc.name.hi, sc.name.te) if n]
            for alias in names + ALIASES.get(sid, []):
                a = alias.lower()
                if len(a) <= 3:
                    if f" {a} " in t:
                        hits.append((sid, None))
                        break
                elif a in t:
                    hits.append((sid, alias if RENAMED.get(a) == sid else None))
                    break
        return hits


@lru_cache
def get_corpus() -> Corpus:
    return Corpus()
